# JPEG-Image-Encryption-and-Decryption-Service-System
本项目是基于 JPEG 编码域的图像加解密服务系统，基于 Flask 框架提供 HTTP 接口服务，实现对 JPEG 图像在 DCT 系数层进行安全加解密。系统支持文件上传、批量加密、批量解密、文件下载和日志记录，可用于云端敏感图像隐私保护、医疗影像安全存储、涉密图像传输等场景。

### 项目目录结构
```
├── data/
│   ├── upload_images/
│   ├── cipher_images/
│   └── decrypt_images/
├── Encryption/
│   └── __init__.py
│   └── AC_encryption.py
│   └── DC_encryption.py
│   └── encryption.py
│   └── invzigzag.py
│   └── utils.py
│   └── zigzag.py
├── Decryption/
│   └── Decompress.py
│   └── DC_decryption.py
│   └── Decompress.py
│   └── decryption.py
│   └── utils.py
├── JPEG/
│   ├── extract.py
│   └── GA.py
│   ├── HuffmanTree.py
│   └── imgSave.py
│   ├── invzigzag.py
│   └── jpeg_dec.py
│   ├── jpeg_enc.py
│   └── jpeg_read.py
│   ├── readJpegBits.py
│   └── utils.py
│   └── zigzag.py
├── server.py
├── debug.py
├── requirements.txt
├── encrypt_log.txt
├── decrypt_log.txt
├── detect_log.txt
└── README.md
```

### 环境要求
- Python 3.8 及以上

### 安装依赖
```bash
pip install -r requirements.txt
```

### 初始化目录（必须）
运行前请创建以下文件夹：
```
data
data/upload_images
data/cipher_images
data/decrypt_images
Encryption
Decryption
JPEG
```

### 启动服务
```bash
python server.py
```
服务地址：http://127.0.0.1:8080

### 接口说明

#### 文件上传接口
- 地址：/upload
- 请求方式：POST
- Content-Type：multipart/form-data
- 参数：file（上传文件）、mode（0=明文，1=密文）

#### 加密接口
- 地址：/encrypt.do
- 请求方式：POST
- Content-Type：application/json
- 参数：files（文件名，多文件逗号分隔）、keys（密钥）

#### 解密接口
- 地址：/decrypt.do
- 请求方式：POST
- Content-Type：application/json
- 参数：files（文件名）、keys（密钥）

#### 文件下载接口
- 地址：/download
- 请求方式：POST
- Content-Type：application/json
- 参数：files（文件名）、mode（0=下载密文，1=下载解密后明文）

### 日志说明
- encrypt_log.txt：加密日志
- decrypt_log.txt：解密日志
- detect_log.txt：调试信息日志

### 项目声明
- 项目名称：JPEG 图像加密解密服务系统
- 项目作者：Chen Yanfeng
- 作者单位：暨南大学网络空间安全学院
- 开发语言：Python
- 框架：Flask
- 核心技术：JPEG 编解码、DCT 域加解密、图像隐私保护


