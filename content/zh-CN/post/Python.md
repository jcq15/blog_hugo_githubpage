---
title: "Python 速查表"
date: 2021-02-22T21:13:04+08:00
draft: false
tags: ["技术"]
categories: ["技术"]
---

我们经常会用到 Python 的各种库，坠痛苦的就是有一些实用的命令记不住，用的时候只好现查，而且这个效率 efficiency…… 所以啊，我整了这么个速查表，以后直接在这里找就好了。

<!--more-->

本贴会持续更新~

> 注意：本文不是教程，而是速查表。

## 实用工具

### datetime

```python
import datetime
```

[官方文档：https://docs.python.org/zh-cn/3/library/datetime.html](https://docs.python.org/zh-cn/3/library/datetime.html)

日期和时间均用datetime.datetime类的对象表示，所以我们先介绍该类的方法

```python
now = datetime.datetime.now()       # 当前时间，类型：datetime.datetime
now.year                            # 获取年（int）
now.month                           # 月
# 类似地还有：day, hour, minute, second, microsecond
```

datetime与字符串之间的转化

```python
# datetime到字符串用strftime（f是format的意思）
now.strftime('%Y-%m-%d %H:%M:%S')   # '2020-09-02 17:45:18'，注意大小写
# 字符串到datetime用strptime
datetime.datetime.strptime('2020-09-02 17:45:18', '%Y-%m-%d %H:%M:%S')
# 这个方法很灵活，根据实际情况来写就行，比如你拿到的数据是'2020年9.2'
str_time = '2020年9.2'
datetime.datetime.strptime(str_time, '%Y年%m.%d') # 就可以正确生成
# 除了%Y，%m这些，还有许多其他类型的代码，完整格式代码请查看https://docs.python.org/zh-cn/3/library/datetime.html#strftime-and-strptime-format-codes 
```

时间差

```python
# timedelta类用来处理时间差
a = datetime.datetime.strptime('2020-09-02 17:45:18', '%Y-%m-%d %H:%M:%S')
b = datetime.datetime.strptime('2020-09-03 17:46:18', '%Y-%m-%d %H:%M:%S')
delta = b - a                        # 返回timedelta对象
delta.days                           # 1
delta.seconds                        # 60
# 注意只有 days. seconds 和 microseconds 会存储在内部，days=1，seconds=60表示这个时间差是1天零60秒，这个结果是唯一的，seconds满一天会自动进位，所以并不会出现days=0，seconds=86460这种情况。
```

## 数据处理

### numpy

这部分主要整理自 https://cs231n.github.io/python-numpy-tutorial/

This tutorial was originally contributed by Justin Johnson

#### 创建

numpy 的核心是 array，它可以表示高维张量，包括向量（rank=1）、矩阵（rank=2）、三阶张量（rank=3）等。我们有很多种方法创建 array：

```python
import numpy as np

a = np.array([1, 2, 3])                  # 通过list创建array
b = np.array([1, 2, 3], [4, 5, 6])       # rank=2，矩阵
print(b)
# [[1 2 3]
#  [4 5 6]]
c = np.zeros((2, 2))                     # 创建2*2的全0矩阵
d = np.ones((1, 2))                      # 1*2的全1矩阵
e = np.full((2, 2), 7)                   # 2*2，元素都是7
f = np.eye(2)                            # 2*2单位矩阵
g = np.random.random((2, 2))             # 2*2随机矩阵
```

#### 索引与切片

可使用list作为下标进行索引，并且支持与python类似的切片操作。

**与list不同的是，array的切片操作返回的是引用，因此修改切片后的值会修改原array的值！**

```python
# Create the following rank 2 array with shape (3, 4)
# [[ 1  2  3  4]
#  [ 5  6  7  8]
#  [ 9 10 11 12]]
a = np.array([[1,2,3,4], [5,6,7,8], [9,10,11,12]])
b = a[:2, 1:3]
# [[2 3]
#  [6 7]]
```

如果某一维度的索引是 int，array会进行降维。要想避免降维可以使用单个元素的 list：

```python
row_r1 = a[1, :]    # 矩阵惨遭降维成向量 
row_r2 = a[1:2, :]  # 如果把1改成1：2，虽然数据一样，但是不降维
row_r3 = a[[1], :]  # 用[1]也不降维
print(row_r1, row_r1.shape)
print(row_r2, row_r2.shape)
print(row_r3, row_r3.shape)
# [5 6 7 8] (4,)
# [[5 6 7 8]] (1, 4)
# [[5 6 7 8]] (1, 4)
```

切片操作得到的永远是原来 array 的 subarray，如果我想重组怎么办呢？比如 [[1, 2], [3, 4]] 我想得到 [[3, 4], [1, 2], [1, 2]]，可以使用 **integer array indexing**：

```python
a = np.array([[1, 2], [3, 4]])
b = a[[1, 0, 0], [0, 1]]
# b是[[3, 4], [1, 2], [1, 2]]，即a的第1行、第0行、第0行拼接
```

**boolean array indexing** 很强大，允许我们进行筛选：

```python
a = np.array([[1,2], [3, 4], [5, 6]])

bool_idx = (a > 2)  # Find the elements of a that are bigger than 2;
                    # this returns a numpy array of Booleans of the same
                    # shape as a, where each slot of bool_idx tells
                    # whether that element of a is > 2.
# [[False False]
# [ True  True]
# [ True  True]]

# We use boolean array indexing to construct a rank 1 array
# consisting of the elements of a corresponding to the True values
# of bool_idx
print(a[bool_idx])

# We can do all of the above in a single concise statement:
print(a[a > 2])

# [3 4 5 6]
# [3 4 5 6]
```

### pandas

```python
import pandas as pd

# 读取excel，第0个sheet
df = pd.read_excel('./filename.xlsx', 0)

# 获取行数、列数
nrow = df.shape[0]
ncol = df.shape[1]

### 切片、筛选、提取数据 ###

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

### sklearn

```python
# 线性回归
from sklearn import linear_model
# 训练数据：X_train, y_train，测试数据：X_test
lm = linear_model.LinearRegression()
model = lm.fit(X_train, y_train)
y_pred = model.predict(X_test)

# 交叉验证
from sklearn.model_selection import cross_val_score
cross_val_score(m, X, y, cv=5, scoring='neg_mean_squared_error') # 5-fold cross validation, m是sklearn的model
```

## 数据结构

### heapq

```python
import heapq as hq

# python的heapq库是在list的基础上添加了堆的操作
# heapq有两种方式创建堆，一种是使用一个空列表，然后使用heapq.heappush()函数把值加入堆中
num = [1,1,4,5,1,4]
heapq.heappush(heap, num)
# 另外一种就是使用heapq.heapify(list)转换列表成为堆结构
heapq.heapify(num)       # 这时候num也变成堆了
```

## 网络/爬虫相关

### requests

```python
import requests

# get请求
html = requests.get('www.baidu.com').text

# get请求可以优雅地加参数
params = {'q': '搜索测试'}
response = requests.get(url='www.google.com/search', params=params).text
```

### BeautifulSoup

```python
from bs4 import BeautifulSoup

# 之前用request获取html

bs = BeautifulSoup(html, 'html.parser')

# 查找标签，返回标签html字符串的list
p_list = bs.findAll('p')						# 查找所有<p>标签
div_list = bs.findAll('div', attrs={'class': 'primary'})		# 带条件筛选<div class='primary'>
# 条件可以是正则表达式
a_list = bs.findAll('a', string='[abs]')		# 字符串包含[abs]
```

### json

```python
import json
import requests

data = requests.get('www.baidu.com').content.decode()	# 某请求返回的字符串格式的json

# 字符串转json
data_js = json.loads(data)
```

