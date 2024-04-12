'''
Author       : Zhijie Yang
Date         : 2024-04-05 23:11:51
LastEditors  : Zhijie Yang
LastEditTime : 2024-04-12 17:06:45
FilePath     : /NL2GQL/generate_smaller_llm_data.py
Description  : 生成训练小模型所需的数据

Copyright (c) 2024 by Zhijie Yang, All Rights Reserved. 
'''
from utils.neo4j_drivers import query_entity_properties_and_relationships
from neo4j import GraphDatabase
from tqdm import tqdm


import pandas as pd
import json
import re
import os


def extract_relationship(cypher:str):
    '''
    description: 从cypher语句中提取关系，因为数据集特殊性，保证关系唯一\n
    cypher: str, cypher语句
    return: str, 关系
    '''
    """match (:ENTITY{name:'鲁迅'})<--(h)-[:Relationship{name:'别名'}]->(q) return distinct q.name limit 1"""
    pattern = r"\[(.*?)\{.*?:'.*?'\}\]"
    relationship = re.findall(pattern, cypher)
    return relationship[0]


def extract_entity(cypher:str):
    '''
    description: 从cypher语句中提取实体，因为数据集特殊性，保证实体唯一\n
    cypher: str, cypher语句
    return: str, 实体
    '''
    """match (:ENTITY{name:'鲁迅'})<--(h)-[:Relationship{name:'别名'}]->(q) return distinct q.name limit 1"""
    pattern = r":ENTITY\{.*?:'(.*?)'\}"
    entity = re.findall(pattern, cypher)
    return entity[0]


def generate_reranker_data():
    '''
    description: 生成重排器数据\n
    数据包括三部分
    return {*}
    '''

    with open('./utils/config.json') as f:
        config = json.load(f)
    # Neo4j数据库连接配置
    uri = config['neo4j_uri']  # Neo4j数据库的URI
    username = config['neo4j_username']  # Neo4j数据库的用户名
    password = config['neo4j_password']  # Neo4j数据库的密码
    # 连接到Neo4j数据库
    driver = GraphDatabase.driver(uri, auth=(username, password))

    with open('./dataset/raw_data/train.json') as f:
        question = json.load(f)

    nodes_schema = """\
    class Entity(Tag):
        def __init__(self, %s):
            %s
"""
    edge_schema = """\
    class %s(Edge):
        def __init__(self, %s):
            %s
"""
    query_skeleton = '''\
    def QUERY(self):
        # MATCH 语句是查询图数据最常用的，可以灵活的描述各种图模式，但是它依赖索引去匹配 NebulaGraph 中的数据模型，性能也还需要调优。
        """
        MATCH <pattern> [<clause_1>]  RETURN <output>  [<clause_2>];
        """
        # Example:match (v:ENTITY)-[]->(t) return v.name, t.name;\n
'''
    limit_skeleton = '''\
    def LIMIT(self):
        """
        YIELD <var> [| LIMIT [<offset_value>,] <number_rows>]
        """
        # Example:{example}\n
'''
    skip_skeleton = '''\
    def SKIP(self):
        """
        RETURN <var> [SKIP <offset>] [LIMIT <number_rows>]
        """
        # Example:{example}\n
'''
    order_by_skeleton = '''\
    def ORDER_BY(self):
        """
        <YIELD clause> ORDER BY <expression> [ASC | DESC] [, <expression> [ASC | DESC] ...]
        """
        # Example:{example}\n
'''
    where_skeleton = '''\
    def WHERE(self):
        """
        WHERE {{<vertex|edge_alias>.<property_name> {{>|==|<|...}} <value>...}}
        """
        # Example:{example}\n
'''
    with_skeleton = '''\
    def WITH(self):
        """
        MATCH $expressions WITH {{nodes()|labels()|...}}
        """
        # Example:{example}\n
'''
    example = '''match (:ENTITY{name:'%s'})--(h) with h order by h.name return distinct h.name skip 1 limit 3'''

    skeleton_map = {'limit': limit_skeleton, 'skip': skip_skeleton, 'order by': order_by_skeleton, 'where': where_skeleton, 'with': with_skeleton}
    
    ret = []
    for q in tqdm(question[13:]):
        try:
            en = extract_entity(q['cypher'])
            _, p, r = query_entity_properties_and_relationships(driver, en)
        except:
            continue
        properties = []
        for _ in p:
            properties.extend(_.strip("[]'").split(','))
        relationships = []
        for _ in r:
            if _[0] not in relationships:
                relationships.append(_[0])
        schema = """# this is the schema of this graph\n# Nodes\nclass Tag():\n"""
        schema += nodes_schema%(','.join(properties),'\n'.join(["self.%s=%s"%(p,'name') for p in properties]))
        schema += """\n# Edge\nclass Edge():\n"""
        schema += '\n'.join([edge_schema%(r, 'name', 'self.name=name') for r in relationships])

        text_schema = """the node type:[{'ENTITY':[%s]}],the edge type:[%s]"""%\
            (','.join(properties),"{"+"},{".join(["'%s':name"%(r) for r in relationships])+"}")

        source_text = """[task]:Please generate the function, clause and class based on the following query and schema.\n"""
        source_text += '[query]:' + q['query'] + '\n'
        source_text += '[schema]:\n' + schema + "\n"

        skeleton = """# the request CRUD function\nclass CRUD():\n"""+query_skeleton
        tmp = """"""
        for k in skeleton_map.keys():
            if k in q['cypher']:
                tmp += skeleton_map[k].format(example=example%en)
        if tmp != '':
            skeleton += '''# the request subfunction\nclass SUBFUNCTION():\n'''+tmp

        ret.append(q)
        ret[-1]['schema'] = schema
        ret[-1]['text_schema'] = text_schema
        ret[-1]['skeleton'] = skeleton
        
    with open('dataset/reranker.json', 'w') as f:
        json.dump(ret, f, ensure_ascii=False, indent=4)


def generate_train_data():
    data = []
    with open('dataset/reranker.json') as f:
        data = json.load(f)
    skeleton = ''
    with open('dataset/skeleton.txt') as f:
        skeleton = f.read()
    for i in tqdm(range(len(data))):
        source_text = "[task]:Please generate the corresponding three-step inference based on the following query, schema and skeleton.\n"
        source_text += '[query]:' + data[i]['query'] + '\n'
        source_text += '[schema]:\n' + data[i]['schema'] + "\n"
        source_text += '[skeleton]:\n' + skeleton + "\n"
        source_text += '[output]:'

        rel = ''
        try:
            rel = extract_relationship(data[i]['cypher'])
        except:
            pass
        response = """\
# the request function:['QUERY']
# the request clause: [%s]
# the request class:['ENTITY']
"""%rel
        data[i]['prompt'] = source_text
        data[i]['response'] = response
        del data[i]['schema']
        del data[i]['skeleton']
        del data[i]['text_schema']

    with open('data/reranker.json', 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)



def main():
    if not os.path.exists('dataset/reranker.json'):
        generate_reranker_data()
    generate_train_data()



if __name__ == "__main__":
    main()
