from Encryption.encryption import encrypt_each_component
from Decryption.decryption import decrypt_each_component
from JPEG.jpeg_enc import JPEG_OBJECT_ENC
from JPEG.jpeg_dec import JPEG_OBJECT_DEC
from flask import Flask, request, jsonify
from datetime import datetime
import os
import base64

app = Flask(__name__)
DATA_FOLDER = 'data'  # 上传文件的存储目录
ALLOWED_EXTENSIONS = {'jpg'}  # 允许上传的文件类型
FILE_MODE = ['cipher_images','decrypt_images']

def encryption(files,keys):
    success = []
    for i in range(len(files)):
        now = datetime.now()
        formatted_now = now.strftime("%Y-%m-%d %H:%M:%S")
        try:
            img_path = os.path.join(os.getcwd(), DATA_FOLDER,'upload_images',files[i])
            image_obj = JPEG_OBJECT_ENC(img_path)

            #--------以下为debug用，后续建议删除--------
            pre_image_leng = len(image_obj.bin_ecs)  # 原始jpeg二进制比特流长度
            pre_num_blocks = image_obj.num_block
            #-----------------------------------------

            [dct_Y,dct_Cb,dct_Cr] = image_obj.jpeg_decode()

            row,col = image_obj.width,image_obj.height
            dct_Y_encrypted,secret_Y = encrypt_each_component(dct_Y,'Y',row,col,keys)
            if image_obj.mode == 34:
                dct_Cb_encrypted,secret_Cb = encrypt_each_component(dct_Cb,'Cb',int(row/2),int(col/2),keys)
                dct_Cr_encrypted,secret_Cr = encrypt_each_component(dct_Cr,'Cr',int(row/2),int(col/2),keys)
            else:
                dct_Cb_encrypted,secret_Cb = encrypt_each_component(dct_Cb,'Cb',row,col,keys)
                dct_Cr_encrypted,secret_Cr = encrypt_each_component(dct_Cr,'Cr',row,col,keys)
            
            image_obj.jpeg_encode(dct_Y_encrypted,dct_Cb_encrypted,dct_Cr_encrypted)
            image_obj.secret_embedding(secret_Y,secret_Cb,secret_Cr)
            cipher_path = os.path.join(os.getcwd(), DATA_FOLDER, 'cipher_images', files[i])
            image_obj.gen_image(cipher_path)

            success.append(files[i])
            with open('./encrypt_log.txt','a') as logger:
                logger.write(formatted_now+'--'+files[i]+'--SUCCESS\n')
            
            #--------以下为debug用，后续建议删除--------
            aft_type_data_len=image_obj.byte_data_len#存进日志
            aft_image_leng=len(image_obj.bin_ecs)#加密后jpeg二进制比特流长度
            aft_num_blocks=image_obj.num_block

            plain_image_size = os.path.getsize(img_path)
            plain_image_size_kb=round(plain_image_size / 1024, 2)
            cipher_file_size = os.path.getsize(cipher_path)  # 获取图像文件大小
            cipher_file_size_kb=round(cipher_file_size / 1024, 2)
            with open('./detect_log.txt', 'a', encoding="utf-8") as logger:
                logger.write(formatted_now +'---调用encryption---文件路径: ' + img_path +'\n')
                logger.write('--------明文图像大小: ' + str(plain_image_size_kb) + ' kb\n')
                logger.write('--------明文比特流长度: ' + str(pre_image_leng) + '\n')
                logger.write('--------密文图像大小: ' + str(cipher_file_size_kb) + ' kb\n')
                logger.write('--------密文比特流长度: ' + str(aft_image_leng) + '\n')
                #logger.write("加密后图像二进制长度：" + str(aft_type_data_len) + '\n')
                #logger.write("加密前后DCT系数矩阵数：" + str(pre_num_blocks) + '->'+str(aft_num_blocks) + '\n')
                
            #-----------------------------------------

        except Exception as e:
            with open('./encrypt_log.txt','a') as logger:
                logger.write(formatted_now+'--'+files[i]+'--ERROR--'+str(e)+'\n')
    return success

def decryption(files,keys):
    success = []
    for i in range(len(files)):
        now = datetime.now()
        formatted_now = now.strftime("%Y-%m-%d %H:%M:%S")
        try:
            img_path = os.path.join(os.getcwd(), DATA_FOLDER,'cipher_images',files[i])
            image_obj = JPEG_OBJECT_DEC(img_path)

            #--------以下为debug用，后续建议删除--------
            pre_image_leng = len(image_obj.bin_ecs)  # 原始jpeg二进制比特流长度
            pre_num_blocks = image_obj.num_block
            #-----------------------------------------

            row,col = image_obj.width,image_obj.height
            #提取秘密信息，并恢复哈夫曼表，ac系数以及重建文件头
            secret_Y,secret_C = image_obj.secret_extract()
            image_obj.restore_image()
            #解密
            [dct_Y,dct_Cb,dct_Cr] = image_obj.jpeg_decode()

            Y_dct_decrypt = decrypt_each_component(dct_Y,secret_Y,'Y',row,col,keys)
            if image_obj.mode == 34:
                Cb_dct_decrypt = decrypt_each_component(dct_Cb,secret_C,'Cb',int(row/2),int(col/2),keys)
                Cr_dct_decrypt = decrypt_each_component(dct_Cr,secret_C,'Cr',int(row/2),int(col/2),keys)
            else:
                Cb_dct_decrypt = decrypt_each_component(dct_Cb,secret_C,'Cb',row,col,keys)
                Cr_dct_decrypt = decrypt_each_component(dct_Cr,secret_C,'Cr',row,col,keys)
            #使用解密后的dct系数编码，并保存图像
            image_obj.jpeg_encode(Y_dct_decrypt,Cb_dct_decrypt,Cr_dct_decrypt)
            image_obj.gen_new_ecs()
            plain_path = os.path.join(os.getcwd(), DATA_FOLDER, 'decrypt_images', files[i])
            image_obj.gen_image(plain_path)
            success.append(files[i])
            with open('./decrypt_log.txt','a') as logger:
                logger.write(formatted_now+'--'+files[i]+'--SUCCESS\n')


            #--------以下为debug用，后续建议删除--------
            aft_type_data_len=image_obj.byte_data_len#存进日志
            aft_image_leng=len(image_obj.bin_ecs)#加密后jpeg二进制比特流长度
            aft_num_blocks=image_obj.num_block

            cipher_file_size = os.path.getsize(img_path)
            cipher_file_size_kb=round(cipher_file_size / 1024, 2)
            plain_image_size = os.path.getsize(plain_path)
            plain_image_size_kb=round(plain_image_size / 1024, 2)

            with open('./detect_log.txt', 'a', encoding="utf-8") as logger:
                logger.write(formatted_now +'---调用decryption---文件路径: ' + img_path +'\n')
                logger.write('--------密文图像大小: ' + str(cipher_file_size_kb) + ' kb\n')
                logger.write('--------密文比特流长度: ' + str(pre_image_leng) + '\n')
                logger.write('--------明文图像大小: ' + str(plain_image_size_kb) + ' kb\n')
                logger.write('--------明文比特流长度: ' + str(aft_image_leng) + '\n')
                #logger.write("加密后图像二进制长度：" + str(aft_type_data_len) + '\n')
                #logger.write("加密前后DCT系数矩阵数：" + str(pre_num_blocks) + '->'+str(aft_num_blocks) + '\n')
                
            #-----------------------------------------
                
        except Exception as e:
            with open('./decrypt_log.txt','a') as logger:
                logger.write(formatted_now+'--'+files[i]+'--ERROR--'+str(e)+'\n')
    return success

@app.route('/encrypt.do', methods=['POST'])
def encrypt():
    # 确保JSON数据被正确提供
    if not request.is_json:
        return jsonify({"message": "Missing JSON in request"}), 400

    # 从JSON数据中获取参数
    data = request.get_json()
    files = data.get('files') # 待加密图像
    keys = data.get('keys') # 密钥
    try:
        files_list = files.split(',')
        assert files_list!= []
    except:
        return jsonify({"message": "Invalid parameters"}), 400

    success = encryption(files_list,keys)
    ret = ','.join(success)
    return jsonify({"message": "Success","results":ret}), 200

@app.route('/decrypt.do', methods=['POST'])
def decrypt():
    # 确保JSON数据被正确提供
    if not request.is_json:
        return jsonify({"message": "Missing JSON in request"}), 400

    # 从JSON数据中获取参数
    data = request.get_json()
    files = data.get('files') # 待加密图像
    keys = data.get('keys') # 密钥
    try:
        files_list = files.split(',')
        assert files_list!= []
    except:
        return jsonify({"message": "Invalid parameters"}), 400

    success = decryption(files_list,keys)
    ret = ','.join(success)
    return jsonify({"message": "Success","results":ret}), 200

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_file():
    # 检查是否有文件在请求中
    if 'file' not in request.files:
        return jsonify({"message": "Missing file"}),400
    file = request.files['file']
    if request.form['mode'] == '0':
        file_path = os.path.join(os.getcwd(), DATA_FOLDER, 'upload_images')
    elif request.form['mode'] == '1':
        file_path = os.path.join(os.getcwd(), DATA_FOLDER, 'cipher_images')
    else:
        return jsonify({"message": "Invalid parameters"}), 400
    # 如果用户没有选择文件，浏览器可能会提交一个没有文件名的空部分
    if file.filename == '':
        return jsonify({"message": "Missing file"}), 400

    if file and allowed_file(file.filename):
        filename = file.filename
        file.save(os.path.join(file_path, filename))

        #--------以下为debug用，后续建议删除--------
        now = datetime.now()
        formatted_now = now.strftime("%Y-%m-%d %H:%M:%S")
        path = os.path.join(file_path, filename)
        image_size = os.path.getsize(path)
        image_size_kb=round(image_size / 1024, 2)
        with open('./detect_log.txt', 'a', encoding="utf-8") as logger:
            logger.write(formatted_now +'---调用upload_file---文件保存路径: ' + path +'\n')
            logger.write('--------图像大小: ' + str(image_size_kb) + ' kb\n')
        #-----------------------------------------

        return jsonify({"message": "Success"}), 200
    else:
        return jsonify({"message": "Uploaded file type not supported"}), 400

@app.route('/download', methods=['POST'])
def download_file():
    now = datetime.now()
    formatted_now = now.strftime("%Y-%m-%d %H:%M:%S")
    # 确保JSON数据被正确提供
    if not request.is_json:
        return jsonify({"message": "Missing JSON in request"}), 400
    data = request.get_json()
    filename = data.get('files') # 待下载的文件
    mode = data.get('mode') # 待下载文件的性质(明文、密文、解密后)
    if mode not in [0,1]:
        return jsonify({"message": "Invalid parameters"}), 400

    file_path = os.path.join(os.getcwd(), DATA_FOLDER, FILE_MODE[mode], filename)
    if not os.path.exists(file_path):
        return jsonify({"message": "File not found"}), 404

    jpeg_file_size = os.path.getsize(file_path)  # 获取图像文件大小
    jpeg_file_size_kb = round(jpeg_file_size / 1024, 2)


    with open(file_path,'rb') as image_file:
        img_bytes = image_file.read()
    base64_img = base64.b64encode(img_bytes).decode('utf-8')
    

    #--------以下为debug用，后续建议删除--------
    now = datetime.now()
    formatted_now = now.strftime("%Y-%m-%d %H:%M:%S")
    #path = os.path.join(file_path, filename)
    image_size = os.path.getsize(file_path)
    image_size_kb=round(image_size / 1024, 2)
    with open('./detect_log.txt', 'a', encoding="utf-8") as logger:
        logger.write(formatted_now +'---调用download---文件保存路径: ' + file_path +'\n')
        logger.write('--------图像大小: ' + str(image_size_kb) + ' kb\n')
    #-----------------------------------------

    return {'data': base64_img, 'code': 1, 'file_name': filename, "file_size_kb": jpeg_file_size_kb}

if __name__ == '__main__':
    # 运行Flask应用，默认地址为http://127.0.0.1:5000/
    app.run(port=8080, debug=True, host='0.0.0.0')