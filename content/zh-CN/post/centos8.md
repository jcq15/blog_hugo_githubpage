---
title: "CentOS 8 配置 tensorflow GPU"
date: 2021-04-02T00:00:26+08:00
draft: false
tags: ["技术"]
categories: ['技术']
---

记录一下给腾讯云 GPU 服务器安装 tensorflow-gpu 的过程。这玩意事挺多。

## 检查必要的东西

检查 Python 版本：

```shell
$ python3
```

腾讯云自带了 Python3.6。如果没有就装一下。

验证系统是否有支持 CUDA 的 GPU：

```shell
$ lspci | grep -i nvidia
```

确认系统已经安装了 gcc：

```shell
$ gcc --version
```

## 安装 CUDA

### 1. 下载

下载 NVIDIA CUDA 工具包，在这找下载链接：

https://developer.nvidia.com/cuda-downloads

我们装 CUDA Toolkit 11.2 Update 2，target_type 选 runfilelocal 即可。

### 2. 安装

**首先禁用 Nouveau 驱动**

```shell
$ vim /etc/modprobe.d/blacklist-nouveau.conf
```

如果已有内容就在最后添加，如果是空文件直接输入：

```
blacklist nouveau
options nouveau modeset=0
```

然后执行

```shell
$ dracut --force
```

安装很简单：

```shell
$ sh cuda_<version>_linux.run
```

输入 accept，之后就一直按 install 与 yes 就行了。**执行安装程序会安装自动安装与 CUDA 对应的驱动，所以请不要单独安装驱动**。

### 3. 设置环境变量

```shell
$ vim /etc/profile
```

文件末尾添加：

```
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
export PATH=/usr/local/cuda-11.2/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda-11.2/lib64:$LD_LIBRARY_PATH
```

执行

```shell
$ source /etc/profile
```

### 4. 测试

```shell
$ nvcc -V
$ nvidia-smi
```

都能看到输出说明大成功，否则完犊子。

## 安装 cudnn

https://developer.nvidia.com/rdp/cudnn-archive

要先注册 nvidia 账号，哈哈。

然后干就完了：

```shell
$ mv cudnn-<version>.solitairetheme8 cudnn-<version>.tgz
$ tar -xzvf cudnn-<version>.tgz 
$ cp cuda/include/cudnn*.h /usr/local/cuda/include
$ cp cuda/lib64/libcudnn* /usr/local/cuda/lib64
$ chmod a+r /usr/local/cuda/include/cudnn*.h /usr/local/cuda/lib64/libcudnn*
```

## 安装 tensorflow-gpu

```shell
$ pip3 install tensorflow-gpu
```

然后菜了，报错 `python setup.py egg_info failed with error code 1`。需要先更新一波 pip：

```shell
$ pip3 install --upgrade setuptools
$ python3 -m pip install --upgrade pip
```

装完了进入 Python，测试一波：

```shell
>>> import tensorflow as tf
>>> tf.test.is_gpu_available()
```

又菜了，他说找不到 `libcusolver.so.10`。我看了一下，`/usr/local/cuda-11.1/lib64/` 里面有个 `libcusolver.so.11`，好家伙，这不是有病嘛，都 11.2 了还在找 .10，封建遗毒啊！来一个骚操作骗他一手：

```shell
$ ln -s /usr/local/cuda-11.2/lib64/libcusolver.so.11 /usr/local/cuda-11.2/lib64/libcusolver.so.10
```

然后就好了。

## 参考文献

[1] https://blog.csdn.net/qq_35540540/article/details/108767800

[2] https://github.com/tensorflow/tensorflow/issues/43947#issuecomment-739617116