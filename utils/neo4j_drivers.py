'''
Author       : Zhijie Yang
Date         : 2023-11-20 06:17:42
LastEditors  : Zhijie Yang
LastEditTime : 2023-12-14 15:12:11
FilePath     : /ChatNeo4j/utils/neo4j_drivers.py
Description  : 

Copyright (c) 2023 by Zhijie Yang, All Rights Reserved. 
'''
from neo4j import GraphDatabase

import Levenshtein
import signal
import json
import re

timeout_seconds = 60

def __get_first_entity(input_string:str)->str:
    '''
    description: 获取问句中的第一个实体\n
    param {str} input_string 问句\n
    return {*} 返回一个List包含识别到的实体
    '''
    match_pattern = r"(\(.+?\)).?-"
    matches = re.findall(match_pattern, input_string)
    matches = matches[0]
    return matches

def __get_last_entity(input_string:str)->str:
    '''
    description: 获取问句中有几个实体\n
    param {str} input_string 问句\n
    return {*} 返回一个List包含识别到的实体
    '''
    match_pattern = r"-.?(\(.+?\))"
    matches = re.findall(match_pattern, input_string)
    matches = matches[-1]
    if len(matches) > 8:
        match_pattern = r"\(([^-]*?):.*?\)"
        matches = re.findall(match_pattern, input_string)
        matches = "(" + matches[-1] + ")"
    return matches

def __get_last_relationship(input_string:str)->str:
    '''
    description: 获取问句中最后一个关系，并为关系添加名称r\n
    param {str} input_string 输入串\n
    return {*} 返回添加了名称之后的查询语句\n
    '''
    match_pattern = r"-(.?)\[.?:(.*?)\]"
    replacement = r"-\1[r:\2]"
    return re.sub(match_pattern, replacement, input_string)

def query_entity_properties_and_relationships(driver:GraphDatabase.driver, name:str):
    entity, properties, relationships = {},[],[]
    # 执行查询
    # 定义超时处理函数
    def timeout_handler(signum, frame):
        raise TimeoutError("Function execution timed out")
    # 注册超时信号处理函数
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_seconds)

    try:
        with driver.session() as session:
            query = """\
                    MATCH (e:ENTITY {name: $name})
                    RETURN e, keys(e) AS properties;
                    """
            result = session.run(query, name=name)
            for record in result:
                entity.update(record['e'])
                properties.append(f"{record['properties']}")

            query = """\
                    MATCH (e:ENTITY {name: $name})-[r]-(q)
                    RETURN {relationshipType:type(r),relationshipName:r.name} AS relationships;
                    """
            result = session.run(query, name=name).data()
            for record in result:
                _ = record["relationships"]
                relationships.append((_['relationshipType'],_['relationshipName']))
    except Exception as e:
        # 将query保存到日志文件中
        with open('./utils/query_log.txt', 'a') as f:
            f.write("init:\terror:" + e + '\n' + query.replace("$name",name) + '\n')
    finally:
        # driver.close()
        
        #取消超时信号的注册
        signal.alarm(0)
    
    return entity['name'], list(set(properties)), list(set(relationships))


def run_query(driver:GraphDatabase.driver, query:str):
    def timeout_handler(signum, frame):
        raise TimeoutError("Function execution timed out")
    # 注册超时信号处理函数
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_seconds)
    try:
        with driver.session() as session:
            result = session.run(query)

            records = []
            # 处理查询结果
            for record in result:
                tmp = record.values()
                records.append(tmp)
    except Exception as e:
        # 将query保存到日志文件中
        raise e
    finally:
        # driver.close()
        # 取消超时信号的注册
        signal.alarm(0)
    # return records
    return records

def query_properties(driver:GraphDatabase.driver, cypher:str):
    def timeout_handler(signum, frame):
        raise TimeoutError("Function execution timed out")
    # 注册超时信号处理函数
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_seconds)
    en_tail_cypher = " return distinct keys({name}) as properties"
    # detail_tail_cypher = " return {name}.{property} as value"
    en_name = ""
    try:
        en_name = __get_last_entity(cypher)
        idx = cypher.find(en_name) + len(en_name)
        sub_cypher = cypher[:idx] + en_tail_cypher.format(name=en_name.strip('()'))
        # detail_sub_cypher = cypher[:idx] + detail_tail_cypher.format(name=en_name.strip('()'))
    except:
        en_name = __get_first_entity(cypher)
        idx = cypher.find(en_name) + len(en_name)
        sub_cypher = cypher[:idx].replace(en_name, en_name[:1] + 'h' + en_name[1:]) + en_tail_cypher.format(name='h')
        # detail_sub_cypher = cypher[:idx].replace(en_name, en_name[:1] + 'h' + en_name[1:]) + detail_tail_cypher.format(name='h')
    try:
        with driver.session() as session:
            result = session.run(sub_cypher)
            ret = {}
            tmp = []
            # 处理查询结果
            for record in result:
                # 访问每个记录的属性
                value = record["properties"]
                tmp = value
            
            # result = session.run(detail_sub_cypher)
            # for record in result:
            #     value = record['value']
            #     ret[tmp] = value
    except Exception as e:
        # 将query保存到日志文件中
        raise e
    finally:
        # driver.close()
        # 取消超时信号的注册
        signal.alarm(0)
    return tmp


def query_relationship(driver:GraphDatabase.driver, cypher:str, query:str):
    def timeout_handler(signum, frame):
        raise TimeoutError("Function execution timed out")
    # 注册超时信号处理函数
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_seconds)
    cypher = cypher.split(' return')[0].split(' with')[0]
    cypher = cypher.strip('- ')
    rel_tail_cypher = "-() return distinct {relationshipType: type(r), relationshipName: r.name} as relationships"
    if cypher.strip('- ')[-1] == ']':
        cypher += '-()-[r]'
        # cypher = __get_last_relationship(cypher.strip("- "))
        sub_cypher = cypher + rel_tail_cypher
    else:
        sub_cypher = cypher.strip('- ') + '-[r]' + rel_tail_cypher
    try:
        with driver.session() as session:
            result = session.run(sub_cypher)
            tmp = {}
            # 处理查询结果
            for record in result:
                # 访问每个记录的属性
                value = record["relationships"]
                if value['relationshipType'] not in tmp:
                    tmp[value['relationshipType']] = []
                tmp[value['relationshipType']].append(value['relationshipName'])
    except Exception as e:
        # 将query保存到日志文件中
        raise e
    finally:
        # driver.close()
        # 取消超时信号的注册
        signal.alarm(0)

    try:
        for k in tmp:
            distances = [(s, Levenshtein.distance(s, query)) for s in tmp[k] if s is not None]
            sorted_distances = sorted(distances, key=lambda x: (x[1], len(x[0])))
            tmp[k] = [s[0] for s in sorted_distances][:20]
    except Exception as e:
        print(e)
    return tmp

if __name__ == "__main__":
    with open('./utils/config.json') as f:
        config = json.load(f)
    # Neo4j数据库连接配置
    uri = config['neo4j_uri']  # Neo4j数据库的URI
    username = config['neo4j_username']  # Neo4j数据库的用户名
    password = config['neo4j_password']  # Neo4j数据库的密码
    # 连接到Neo4j数据库
    driver = GraphDatabase.driver(uri, auth=(username, password),max_connection_lifetime=3600*24*30,keep_alive=True)

    query = """match (:ENTITY{name:'夏景春'})-"""
    tmp = """match (:ENTITY{name:'夏景春'})<-[:Relationship{name:'中文名称'}]-(p)-[:Relationship{name:'职业'}]->(m) return distinct m.name limit 1"""

    # print(query_properties(driver, query))
    print(query_relationship(driver, query, tmp))
    driver.close()