from Crypto.Cipher import AES
import binascii

def xor_bytes(a: bytes, b: bytes) -> bytes:
    """
    两个字节串逐字节异或（长度需相同）
    :param a: 字节串1
    :param b: 字节串2
    :return: 异或后的字节串
    """
    return bytes([x ^ y for x, y in zip(a, b)])

def aes_cbc_decrypt(key_hex: str, ciphertext_hex: str) -> str:
    """
    AES CBC模式解密（自行实现CBC逻辑，底层用AES ECB）
    :param key_hex: 16进制编码的密钥
    :param ciphertext_hex: 16进制编码的密文（含16字节IV）
    :return: 解密后的明文（UTF-8编码）
    """
    # 1. 十六进制转字节
    key = binascii.unhexlify(key_hex)
    ciphertext = binascii.unhexlify(ciphertext_hex)
    
    # 2. 提取IV（前16字节）和实际密文
    iv = ciphertext[:16]
    cipher_blocks = ciphertext[16:]
    
    # 3. 初始化AES ECB解密器（CBC解密核心是ECB解每个分组）
    aes_ecb = AES.new(key, AES.MODE_ECB)
    
    plaintext = b""
    prev_block = iv  # 初始前一个块为IV
    
    # 4. 分块解密（每组16字节）
    for i in range(0, len(cipher_blocks), 16):
        curr_block = cipher_blocks[i:i+16]
        # ECB解密当前密文块
        decrypted_block = aes_ecb.decrypt(curr_block)
        # 与前一个块异或得到明文块
        plain_block = xor_bytes(decrypted_block, prev_block)
        plaintext += plain_block
        # 更新前一个块为当前密文块
        prev_block = curr_block
    
    # 5. 去除PKCS#5填充（填充值=填充长度）
    padding_len = plaintext[-1]
    plaintext = plaintext[:-padding_len]
    
    return plaintext.decode("utf-8")

def aes_ctr_decrypt(key_hex: str, ciphertext_hex: str) -> str:
    """
    AES CTR模式解密（自行实现CTR逻辑，底层用AES ECB）
    :param key_hex: 16进制编码的密钥
    :param ciphertext_hex: 16进制编码的密文（含16字节初始计数器）
    :return: 解密后的明文（UTF-8编码）
    """
    # 1. 十六进制转字节
    key = binascii.unhexlify(key_hex)
    ciphertext = binascii.unhexlify(ciphertext_hex)
    
    # 2. 提取初始计数器（前16字节）和实际密文
    init_counter = int.from_bytes(ciphertext[:16], byteorder="big")
    cipher_data = ciphertext[16:]
    
    # 3. 初始化AES ECB加密器（CTR用ECB加密计数器生成密钥流）
    aes_ecb = AES.new(key, AES.MODE_ECB)
    
    plaintext = b""
    counter = init_counter
    
    # 4. 生成密钥流并异或解密
    for i in range(0, len(cipher_data), 16):
        # 计数器转16字节大端字节串
        counter_bytes = counter.to_bytes(16, byteorder="big")
        # 加密计数器生成密钥流块
        keystream = aes_ecb.encrypt(counter_bytes)
        # 取当前密文块（最后一块可能不足16字节）
        curr_cipher = cipher_data[i:i+16]
        # 密钥流与密文异或得到明文块
        plain_block = xor_bytes(keystream[:len(curr_cipher)], curr_cipher)
        plaintext += plain_block
        # 计数器递增
        counter += 1
    
    return plaintext.decode("utf-8")

# 测试四个题目
if __name__ == "__main__":
    # 第1题：CBC解密
    key1 = "140b41b22a29beb4061bda66b6747e14"
    cipher1 = "4ca00ff4c898d61e1edbf1800618fb2828a226d160dad07883d04e008a7897ee2e4b7465d5290d0c0e6c6822236e1daafb94ffe0c5da05d9476be028ad7c1d81"
    res1 = aes_cbc_decrypt(key1, cipher1)
    print("第1题答案：", res1)
    
    # 第2题：CBC解密
    cipher2 = "5b68629feb8606f9a6667670b75b38a5b4832d0f26e1ab7da33249de7d4afc48e713ac646ace36e872ad5fb8a512428a6e21364b0c374df45503473c5242a253"
    res2 = aes_cbc_decrypt(key1, cipher2)
    print("第2题答案：", res2)
    
    # 第3题：CTR解密
    key3 = "36f18357be4dbd77f050515c73fcf9f2"
    cipher3 = "69dda8455c7dd4254bf353b773304eec0ec7702330098ce7f7520d1cbbb20fc388d1b0adb5054dbd7370849dbf0b88d393f252e764f1f5f7ad97ef79d59ce29f5f51eeca32eabedd9afa9329"
    res3 = aes_ctr_decrypt(key3, cipher3)
    print("第3题答案：", res3)
    
    # 第4题：CTR解密
    cipher4 = "770b80259ec33beb2561358a9f2dc617e46218c0a53cbeca695ae45faa8952aa0e311bde9d4e01726d3184c34451"
    res4 = aes_ctr_decrypt(key3, cipher4)
    print("第4题答案：", res4)