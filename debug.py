from server import encryption,decryption
from JPEG.jpeg_enc import JPEG_OBJECT_ENC
import os

import time
DATA_FOLDER = 'data'  # 上传文件的存储目录

start = time.time()
img_path = os.path.join(os.getcwd(), DATA_FOLDER,'upload_images','2.jpg')
image_obj = JPEG_OBJECT_ENC(img_path)
[dct_Y,dct_Cb,dct_Cr] = image_obj.jpeg_decode()
encryption(['2.jpg'],'123456')
decryption(['2.jpg'],'123456')
end = time.time()
print(end-start)