---
title: "Python数据处理速查表"
date: 2022-05-23
draft: false
tags: [
"技术",
]
categories: ["技术"]
math: false
---

以前的速查表有点乱，近期重整一下。

<!--more-->

## Pandas

```python
import pandas as pd
```

### 数据读取

```python
df = pd.read_excel('filepath/name.xlsx', 0, header=0)
# 第0个sheet
# header=0: 第一行为表头，header=None：无表头

df = pd.read_csv('file.csv')

df = pd.read_csv('file.txt', sep='\t')
```

新建 dataframe，从 dict 直接创建：

```python
data = {
    'name': ['李华', '二傻子'],
    'age': [114, 514]
}
df = pd.Dataframe(data)
```

### 索引与切片

```python
# 直接通过'[]'，字符串表示列，数字表示行
df['price']       				# 选取名字为'price'的列
df[['name', 'price']]			# 选取多列，把列名放在list里
df[:2]							# 第0行和第1行，这里和list的切片操作一样

# iloc和loc：索引用iloc，列名用loc。iloc和loc的优势是可以进行筛选
# loc用法：df.loc[index, column_name]
# 一个大坑：loc的行索引是闭区间，而不是python通用的左闭右开（但iloc是正常的）
df.loc[2, 'price']				# 第2行，名字为'price'的列
df.loc[[2,3],['name','price']]  # index和column_name都可灵活使用list或切片
df.loc[df['price']<100,'name']  # 筛选，注意筛选条件是针对行的

# iloc用法：只要把loc的列名改成索引
df.iloc[df['price']<100, 2:5]   # 一样可以灵活组合list和切片
df.iloc[df['price']<100 | df['price']>200]  # 筛选条件'|'表示或，'&'表示与
```

### 删除

```python
df.drop(columns=['name', 'gender'], inplace=True) # 列
df.drop(index=[0, 1], inplace=True)   # 行
df.drop(df[df['age'] > 80].index)     # 按条件删除
```

### 预处理

描述性统计

```python
df.count()    # 非空观测数量
df.sum()      # 和，可指定axis；mean, median, mode 同理
df.std()      # 标准差
df.min()      # max
```

缺失值

```python
df.isna.sum()   # 每列缺失值个数

df.fillna(0)    # NaN用0填充
df.fillna(df.mean())

df.isnull().any()     # 有缺失值的列
df.isnull().T.any()   # 有缺失值的行
```

异常值

```python
# 3σ
zscore = (df['salary'] - df['salary'].mean()) / df['salary'].std()
zscore.abs() > 3    # 是outlier的mask
```

重复值

```python
df.drop_duplicates(['name', 'age'], 'first', inplace=True)
# subset用来指定特定的列，默认所有列
# keep : {‘first’, ‘last’, False}, default ‘first’，保留第一个
```

