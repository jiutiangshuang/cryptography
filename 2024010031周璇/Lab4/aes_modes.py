from Crypto.Cipher import AES
import binascii

def pkcs5_unpad(data):
    """移除PKCS#5填充，严格按照实验要求实现"""
    padding_length = data[-1]
    return data[:-padding_length]

def aes_cbc_decrypt(ciphertext_hex, key_hex):
    """自行实现AES-CBC模式解密，仅使用AES-ECB基础功能"""
    key = binascii.unhexlify(key_hex)
    ciphertext = binascii.unhexlify(ciphertext_hex)
    
    # 1. 提取前16字节作为IV
    iv = ciphertext[:16]
    actual_ciphertext = ciphertext[16:]
    
    # 2. 初始化AES-ECB解密器
    cipher = AES.new(key, AES.MODE_ECB)
    
    plaintext = b""
    previous_block = iv
    
    # 3. 分块解密并异或前一个密文块
    for i in range(0, len(actual_ciphertext), 16):
        current_cipher_block = actual_ciphertext[i:i+16]
        decrypted_block = cipher.decrypt(current_cipher_block)
        plaintext_block = bytes(a ^ b for a, b in zip(decrypted_block, previous_block))
        plaintext += plaintext_block
        previous_block = current_cipher_block
    
    # 4. 移除PKCS#5填充
    return pkcs5_unpad(plaintext).decode('utf-8')

def aes_ctr_decrypt(ciphertext_hex, key_hex):
    """自行实现AES-CTR模式解密，仅使用AES-ECB基础功能"""
    key = binascii.unhexlify(key_hex)
    ciphertext = binascii.unhexlify(ciphertext_hex)
    
    # 1. 提取前16字节作为初始计数器
    nonce = ciphertext[:16]
    actual_ciphertext = ciphertext[16:]
    
    # 2. 初始化AES-ECB加密器
    cipher = AES.new(key, AES.MODE_ECB)
    
    plaintext = b""
    counter = int.from_bytes(nonce, byteorder='big')
    
    # 3. 生成密钥流并与密文异或
    for i in range(0, len(actual_ciphertext), 16):
        counter_bytes = counter.to_bytes(16, byteorder='big')
        keystream_block = cipher.encrypt(counter_bytes)
        cipher_block = actual_ciphertext[i:i+16]
        plaintext_block = bytes(a ^ b for a, b in zip(cipher_block, keystream_block))
        plaintext += plaintext_block
        counter += 1
    
    return plaintext.decode('utf-8')

if __name__ == "__main__":
    print("=== AES CBC & CTR 解密结果 ===")
    
    # 第1题 CBC
    key1 = "140b41b22a29beb4061bda66b6747e14"
    cipher1 = "4ca00ff4c898d61e1edbf1800618fb2828a226d160dad07883d04e008a7897ee2e4b7465d5290d0c0e6c6822236e1daafb94ffe0c5da05d9476be028ad7c1d81"
    print("第1题答案：", aes_cbc_decrypt(cipher1, key1))
    
    # 第2题 CBC
    cipher2 = "5b68629feb8606f9a6667670b75b38a5b4832d0f26e1ab7da33249de7d4afc48e713ac646ace36e872ad5fb8a512428a6e21364b0c374df45503473c5242a253"
    print("第2题答案：\n", aes_cbc_decrypt(cipher2, key1))
    
    # 第3题 CTR
    key3 = "36f18357be4dbd77f050515c73fcf9f2"
    cipher3 = "69dda8455c7dd4254bf353b773304eec0ec7702330098ce7f7520d1cbbb20fc388d1b0adb5054dbd7370849dbf0b88d393f252e764f1f5f7ad97ef79d59ce29f5f51eeca32eabedd9afa9329"
    print("第3题答案：", aes_ctr_decrypt(cipher3, key3))
    
    # 第4题 CTR
    cipher4 = "770b80259ec33beb2561358a9f2dc617e46218c0a53cbeca695ae45faa8952aa0e311bde9d4e01726d3184c34451"
    print("第4题答案：", aes_ctr_decrypt(cipher4, key3))
    
    input("\n按回车键关闭窗口...")