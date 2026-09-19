---
title: "一触即达：用 YubiKey 打造 Windows 自动解锁与 SSH 安全登录"
date: 2025-04-17
draft: false
tags: ["技术"]
math: false
categories: ['技术']
---

一直拖着桌面上一枚尘封已久的 YubiKey，却不知道该怎么用才最有价值。最近突发奇想：既要让它在 Windows 开机时“自动敲密码”，又要用它完成 SSH 登录时的硬件签名。经过折腾，终于把这两项功能都跑通了，特此记录，方便自己今后查阅，也给有同样需求的你做个参考。

<!--more-->

## Yubikey 是啥？能吃吗？

YubiKey 是由 Yubico 推出的一款硬件安全钥匙，支持 FIDO U2F/FIDO2、OpenPGP、PIV 等多种认证协议。它能将私钥或静态密码安全地存储在硬件中，通过物理触摸即可完成网站登录、SSH 认证、Windows 开机等场景下的双因素或无密认证。由于密钥始终在设备内不外泄，能有效防止钓鱼攻击与远程入侵。

## 环境与工具

- **系统**：Windows 11
- **硬件**：YubiKey 5C 和 Yubikey 5C Nano （俩 YubiKey 分别生成两套 SSH 密钥，其中一枚作为主用，另一枚作为备份，确保即使主钥匙被城管炸了也能无缝继续安全访问）
- **软件**：
    - [Yubikey Manager](https://www.yubico.com/support/download/yubikey-manager/): Yubico 官方管理软件儿
    - [Yubikey Manager CLI](https://developers.yubico.com/yubikey-manager/): 官方命令行工具
    - [OpenSC](https://github.com/OpenSC/OpenSC/releases): 一个开源的智能卡儿工具包儿，要用它调用 Yubikey 进行 SSH 认证

## 一、自动输入 Windows 开机密码

这个如倒立拉屎一样简单。利用 Yubikey 的 Static Password 功能，原理是用手一碰它就模拟键盘操作输入一串儿预定的字符串儿。

1. **配置 Static Password**
    - 打开 YubiKey Manager，选择 **Applications → OTP → Configure**。
    - 在 **Static Password** 里猪入你的 Windows 登录密码，保存。
2. **开机／锁屏时使用**
    - 将 YubiKey 插入任意 USB 接口。
    - 启动或唤醒 Windows，光标定位在密码输入框时，轻触 YubiKey。
    - 它就会像键盘一样，自动输入你配置的密码。无需额外敲击，节省时间又可靠。

> **安全小贴士**：静态密码无需 PIN 解锁，但只有在你“真·触摸”时才会输出，防止远程被滥用。


## 二、基于 PIV 的 SSH 安全登录

这个功能利用 YubiKey 的 PIV（智能卡）功能，将私钥安全地存放在硬件中，SSH 客户端通过 PKCS#11 调用它。

### 1. 使用 Yubikey 生成密钥对儿

安装 [Yubikey Manager CLI](https://developers.yubico.com/yubikey-manager/) 后，在环境变量中添加 `C:\Program Files\Yubico\YubiKey Manager\ykman.exe`，就可以用 `ykman` 了。

每个YubiKey出厂默认设置了PIN为123456，最好修改一下：

```shell
ykman piv access change-pin --pin 123456 --new-pin 654321
```

然后生成密钥对儿：

```shell
ykman piv keys generate --algorithm RSA2048 --pin-policy once --touch-policy always 9a yubikey_main_pubkey.pem
```

提示输入 Management key 直接回车即可。

然后认证：

```shell
ykman piv certificates generate --subject "CN=yubikey_main" 9a yubikey_main_pubkey.pem
```

提示输入 Management key 直接回车，然后输入 PIN，然后让你摸一摸它，摸完了它就结束了。

### 2. 启用并启动 ssh-agent

首先下载安装[OpenSC](https://github.com/OpenSC/OpenSC/releases)。然后在 **PowerShell（管理员）** 中执行：

```powershell
Set-Service -Name ssh-agent -StartupType Automatic
Start-Service ssh-agent
Get-Service ssh-agent  # 确认正在运行
```

### 3. 加载 PIV 私钥

在 **PowerShell** 中：

```powershell
ssh-add -s "C:\Program Files\OpenSC Project\OpenSC\pkcs11\opensc-pkcs11.dll"
```

当提示 `Enter passphrase for PKCS#11:` 时，输入 Yubikey 的 PIN，回车。

**验证**：

```powershell
ssh-add -L
```

应能看到 public key，把它放在该放的地方即可。

### 4. 日了狗的大坑

这里有个日了狗的大坑，OpenSC 的路径是 

```
C:/Program Files/OpenSC Project/OpenSC/pkcs11/opensc-pkcs11.dll
```

敏感肌可能已经发现了，这个路径里有空格儿，它放进 ssh_config 里不能被正确识别！而且 ssh_config 不支持加引号或转义！强迫症儿又不想挪动文件位置。好在 Windows 会给 Program Files、OpenSC Project 这类带空格的目录自动分配一个短名称。

在 CMD 里运行：

```shell
for %I in ("C:\Program Files\OpenSC Project\OpenSC\pkcs11\opensc-pkcs11.dll") do @echo %~sI
```

他会输出无空格路径，类似这个：

```
C:\PROGRA~1\OPENSC~1\OpenSC\pkcs11\OPENSC~1.DLL
```

用它进行下一步就行了。

### 4. 配置 SSH 连接

在 `C:\Users\<用户名>\.ssh\config` 中增加一条儿配置：

```text
Host server_name
    HostName server.example.com
    User youruser
    PKCS11Provider C:\PROGRA~1\OPENSC~1\OpenSC\pkcs11\OPENSC~1.DLL
```

保存后直接

```powershell
ssh server_name
```

如果一切配置正确，Yubikey 会闪烁，触摸 Yubikey 即可认证成功并登录！

### 5. 配置备用的 Yubikey

如果你像我一样打算弄俩 Yubikey 备份，可以换下一个重复操作。 **要拔出来再插进去新的，两根一起插 Yubikey Manager 会受不了**。

```shell
ykman piv access change-pin --pin 123456 --new-pin 654321
ykman piv keys generate --algorithm RSA2048 --pin-policy once --touch-policy always 9a pubkey.pem
ykman piv certificates generate --subject "CN=yubico" 9a pubkey.pem
ssh-add -s "C:\Program Files\OpenSC Project\OpenSC\pkcs11\opensc-pkcs11.dll"
ssh-add -L
```

不知道是我操作不对还是 feature，OpenSC 只能存储一个 key，新来的会覆盖原来的。但问题不大。我们把备用的 public key 也放到服务器上，然后拔掉，插入主 key，再运行一次

```
ssh-add -s "C:\Program Files\OpenSC Project\OpenSC\pkcs11\opensc-pkcs11.dll"
```

如果需要换另一把 key，插进去后重新运行一次上述命令即可。多么简（ma）单（fan）！

## 结语

到此，已经给 YubiKey 配置了**Windows 自动解锁**与**SSH 硬件签名**的功能，并且有另外一把 YubiKey 做备份。以后再也不怕开机忘记密码，也不用担心在服务器间敲来敲去。插上即用、轻触即通，是我最近最满意的个人效率利器。希望这篇分享能帮到你，让你的 YubiKey 也发挥出一触即达的魔力！
