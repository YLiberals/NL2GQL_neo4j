'''
Author       : Zhijie Yang
Date         : 2024-04-05 23:11:51
LastEditors  : Zhijie Yang
LastEditTime : 2024-04-06 00:52:53
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


def extract_entity(cypher:str):
    '''
    description: 从cypher语句中提取实体，因为数据集特殊性，保证实体唯一\n
    cypher: str, cypher语句
    return: str, 实体
    '''
    """match (:ENTITY{name:'100个空前最爱'})-[:Tag{name:'标签'}]-> (h) with h order by h.name where h.name <> '益智游戏' return h.name"""
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
    ret = []
    for q in tqdm(question[:]):
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
                relationships.append(_[0].strip("'"))
        schema = """# this is the schema of this graph\n# Nodes\nclass Tag():\n"""
        schema += nodes_schema%(','.join(properties),'\n'.join(["self.%s=%s"%(p,p) for p in properties]))
        schema += """\n# Edge\nclass Edge():\n"""
        schema += '\n'.join([edge_schema%(r,'name','self.name=name') for r in relationships])
        text_schema = """the node type:[{'ENTITY':[%s]}],the edge type:[%s]"""%\
            (','.join(properties),"{"+"},{".join(["'%s':[name]"%(r) for r in relationships])+"}")

        source_text = """[task]:Please generate the function, clause and class based on the following query and schema.\n"""
        source_text += '[query]:' + q['query'] + '\n'
        source_text += '[schema]:\n' + schema + "\n"
        ret.append(q)
        ret[-1]['schema'] = schema
        ret[-1]['text_schema'] = text_schema

    with open('dataset/reranker/train.json', 'w') as f:
        json.dump(ret, f, ensure_ascii=False, indent=4)


def main():
    generate_reranker_data()


if __name__ == "__main__":
    main()