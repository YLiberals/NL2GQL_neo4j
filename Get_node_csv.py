'''
Author       : Zhijie Yang
Date         : 2024-04-12 17:01:16
LastEditors  : Zhijie Yang
LastEditTime : 2024-04-12 17:10:11
FilePath     : /NL2GQL/Get_node_csv.py
Description  : 获取实体csv文件

Copyright (c) 2024 by Zhijie Yang, All Rights Reserved. 
'''
import pandas as pd
import json
import re


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


def get_node_csv():
    '''
    description: 获取实体csv文件
    return: pd.DataFrame, 实体csv文件
    '''
    with open('./dataset/raw_data/test.json') as f:
        data = json.load(f)


    entities = []
    for d in data:
        entities.append(extract_entity(d['cypher']))

    node_csv = pd.DataFrame(entities, columns=['entity'])
    node_csv.to_csv('./dataset/entities.csv',index=False)


def main():
    get_node_csv()


if __name__=="__main__":
    main()
