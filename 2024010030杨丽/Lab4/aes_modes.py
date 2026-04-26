import binascii

# 自动尝试两种导入方式，彻底解决模块找不到问题
try:
    from Cryptodome.Cipher import AES
except ImportError:
    try:
        from Crypto.Cipher import AES
    except ImportError:
        raise ImportError(
            "哎呀，好像还是找不到 Crypto 模块！\n"
            "请在终端运行：python -m pip install pycryptodomex --user"
        )

def pkcs7_unpad(data: bytes) -> bytes:
    """PKCS#7 去填充，带安全校验"""
    if not data:
        raise ValueError("数据为空，无法去填充")
    pad_len = data[-1]
    if pad_len < 1 or pad_len > 16:
        raise ValueError(f"无效的填充长度: {pad_len}")
    if any(b != pad_len for b in data[-pad_len:]):
        raise ValueError("PKCS#7 填充校验失败，数据可能被篡改")
    return data[:-pad_len]

def aes_cbc_decrypt(key_hex: str, cipher_hex: str) -> str:
    """手动实现 AES-CBC 解密"""
    key = binascii.unhexlify(key_hex)
    cipher_data = binascii.unhexlify(cipher_hex)
    
    iv = cipher_data[:16]
    ciphertext = cipher_data[16:]
    
    # 严格检查密文长度是否为 16 字节的倍数
    if len(ciphertext) % 16 != 0:
        raise ValueError(f"CBC 模式密文长度必须是16的倍数，当前长度: {len(ciphertext)}")
    
    cipher = AES.new(key, AES.MODE_ECB)
    plaintext = b""
    prev_block = iv
    
    for i in range(0, len(ciphertext), 16):
        cipher_block = ciphertext[i:i+16]
        decrypted_block = cipher.decrypt(cipher_block)
        plain_block = bytes(a ^ b for a, b in zip(decrypted_block, prev_block))
        plaintext += plain_block
        prev_block = cipher_block
    
    return pkcs7_unpad(plaintext).decode("utf-8")

def aes_ctr_decrypt(key_hex: str, cipher_hex: str) -> str:
    """手动实现 AES-CTR 解密"""
    key = binascii.unhexlify(key_hex)
    cipher_data = binascii.unhexlify(cipher_hex)
    
    nonce = cipher_data[:16]
    ciphertext = cipher_data[16:]
    
    cipher = AES.new(key, AES.MODE_ECB)
    plaintext = b""
    # CTR 模式标准拆分：前8字节随机数，后8字节计数器
    nonce_part = nonce[:8]
    counter = int.from_bytes(nonce[8:], byteorder="big")
    
    for i in range(0, len(ciphertext), 16):
        # 生成当前计数器块
        counter_bytes = counter.to_bytes(8, byteorder="big")
        keystream_input = nonce_part + counter_bytes
        keystream_block = cipher.encrypt(keystream_input)
        
        # 异或解密（支持最后一块不足16字节）
        cipher_block = ciphertext[i:i+16]
        plain_block = bytes(a ^ b for a, b in zip(cipher_block, keystream_block))
        plaintext += plain_block
        
        counter += 1
    
    return plaintext.decode("utf-8")

if __name__ == "__main__":
    # 第1、2题：CBC解密
    key_cbc = "140b41b22a29beb4061bda66b6747e14"
    cipher1 = "4ca00ff4c898d61e1edbf1800618fb2828a226d160dad07883d04e008a7897ee2e4b7465d5290d0c0e6c6822236e1daafb94ffe0c5da05d9476be028ad7c1d81"
    cipher2 = "5b68629feb8606f9a6667670b75b38a5b4832d0f26e1ab7da33249de7d4afc48e713ac646ace36e872ad5fb8a512428a6e21364b0c374df45503473c5242a253"
    
    print("第1题答案：", aes_cbc_decrypt(key_cbc, cipher1))
    print("第2题答案：", aes_cbc_decrypt(key_cbc, cipher2))
    
    # 第3、4题：CTR解密
    key_ctr = "36f18357be4dbd77f050515c73fcf9f2"
    cipher3 = "69dda8455c7dd4254bf353b773304eec0ec7702330098ce7f7520d1cbbb20fc388d1b0adb5054dbd7370849dbf0b88d393f252e764f1f5f7ad97ef79d59ce29f5f51eeca32eabedd9afa9329"
    cipher4 = "770b80259ec33beb2561358a9f2dc617e46218c0a53cbeca695ae45faa8952aa0e311bde9d4e01726d3184c34451"
    
    print("第3题答案：", aes_ctr_decrypt(key_ctr, cipher3))
    print("第4题答案：", aes_ctr_decrypt(key_ctr, cipher4))