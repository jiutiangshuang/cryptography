# ====================== Lab11 数字签名完整实验 ======================
# 环境初始化，清空历史残留文件
mkdir -p ~/cryptography-lab11
cd ~/cryptography-lab11
rm -f *.pem *.bin *.txt

# -------------------------- 任务一：生成两组RSA密钥 --------------------------
# 1.生成签名私钥（私钥操作，不加-pubin）
openssl genrsa -out signature_private_key.pem 2048
# 查看签名私钥完整文本
openssl rsa -in signature_private_key.pem -text -noout
# 从私钥导出签名公钥（读取私钥，无-pubin）
openssl rsa -in signature_private_key.pem -pubout -out signature_public_key.pem
# 查看签名公钥完整文本（读取公钥，加-pubin）
openssl rsa -pubin -in signature_public_key.pem -text -noout
# 查看签名密钥文件大小
ls -lh signature_private_key.pem signature_public_key.pem

# 2.生成加密私钥（私钥操作，不加-pubin）
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out encryption_private_key.pem
# 导出加密公钥（读取私钥，无-pubin）
openssl rsa -in encryption_private_key.pem -pubout -out encryption_public_key.pem
# 查看加密密钥文件大小
ls -lh encryption_private_key.pem encryption_public_key.pem
【截图：keygen.png】# 包含全部密钥生成、导出、ls查看输出，终端放大清晰

# -------------------------- 任务二：明文创建 + RSA-OAEP加密 --------------------------
# 替换为你的姓名+学号
echo "这是一条重要消息，需要签名保护。发送者：张三，学号：2024010001" > message.txt
# 打印原始明文
cat message.txt
# RSA-OAEP加密（读取公钥，加-pubin，padding固定oaep）
openssl pkeyutl -encrypt -pubin -inkey encryption_public_key.pem -in message.txt -out encrypted_message.bin -pkeyopt rsa_padding_mode:oaep
# 查看密文文件大小
ls -lh encrypted_message.bin
# 十六进制打印密文前两行
xxd encrypted_message.bin | head -2
【截图：encrypt.png】# 明文、加密命令、密文大小、十六进制密文完整输出

# -------------------------- 任务三：密文SHA256哈希 + 私钥签名 --------------------------
# 3.1 计算密文SHA256哈希（仅SHA256）
openssl dgst -sha256 encrypted_message.bin
【截图：hash.png】# 单独完整截取本条哈希输出，留存完整哈希值

# 3.2 使用签名私钥对密文生成SHA256签名（私钥操作，无-pubin）
openssl dgst -sha256 -sign signature_private_key.pem -out signature.bin encrypted_message.bin
# 查看签名文件大小
ls -lh signature.bin
【截图：sign.png】# 签名生成命令、signature.bin大小输出

# -------------------------- 任务四：验签、篡改测试、解密（严格不破坏原始密文） --------------------------
# 4.1 原始密文正常验签（读取公钥，加-pubin）
openssl dgst -sha256 -verify signature_public_key.pem -signature signature.bin encrypted_message.bin
【截图：verify_ok.png】# 必须输出 Verified OK，完整窗口截图

# 4.2 篡改测试：复制全新文件修改，绝不改动原始encrypted_message.bin
cp encrypted_message.bin tampered_encrypted_message.bin
# 向复制出的新文件末尾添加字符篡改
printf 'x' >> tampered_encrypted_message.bin
# 使用原始签名验证篡改后的文件
openssl dgst -sha256 -verify signature_public_key.pem -signature signature.bin tampered_encrypted_message.bin
【截图：verify_fail.png】# 必须输出 Verification failure，完整窗口截图

# 4.3 RSA-OAEP解密原始密文（私钥操作，无-pubin，padding和加密统一oaep）
openssl pkeyutl -decrypt -inkey encryption_private_key.pem -in encrypted_message.bin -out decrypted_message.txt -pkeyopt rsa_padding_mode:oaep
# 打印解密后明文
cat decrypted_message.txt
# 比对原始明文与解密明文是否完全一致
cmp message.txt decrypted_message.txt && echo "解密结果与原始明文完全一致"
# 查看全部业务文件
ls -lh message.txt encrypted_message.bin signature.bin decrypted_message.txt
【截图：decrypt.png】# 解密命令、解密文本、一致提示、全部文件列表
