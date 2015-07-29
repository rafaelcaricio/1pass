from base64 import b64decode
from hashlib import md5

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.hashes import SHA1
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

_backend = default_backend()

class SaltyString(object):
    SALTED_PREFIX = b"Salted__"
    ZERO_INIT_VECTOR = b"\x00" * 16

    def __init__(self, base64_encoded_string):
        decoded_data = b64decode(base64_encoded_string)
        if decoded_data.startswith(self.SALTED_PREFIX):
            self.salt = decoded_data[8:16]
            self.data = decoded_data[16:]
        else:
            self.salt = self.ZERO_INIT_VECTOR
            self.data = decoded_data


class EncryptionKey(object):
    MINIMUM_ITERATIONS = 1000

    def __init__(self, data, iterations=0, validation="", identifier=None,
                 level=None):
        self.identifier = identifier
        self.level = level
        self._encrypted_key = SaltyString(data)
        self._decrypted_key = None
        self._set_iterations(iterations)
        self._validation = validation

    def unlock(self, password):
        key, iv = self._derive_pbkdf2(password)

        self._decrypted_key = self._aes_decrypt(
            key=key,
            iv=iv,
            encrypted_data=self._encrypted_key.data,
        )
        return self._validate_decrypted_key()

    def decrypt(self, b64_data):
        encrypted = SaltyString(b64_data)
        key, iv = self._derive_openssl(self._decrypted_key, encrypted.salt)
        return self._aes_decrypt(key=key, iv=iv, encrypted_data=encrypted.data)

    def _set_iterations(self, iterations):
        self.iterations = max(int(iterations), self.MINIMUM_ITERATIONS)

    def _validate_decrypted_key(self):
        return self.decrypt(self._validation) == self._decrypted_key

    def _aes_decrypt(self, key, iv, encrypted_data):
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=_backend)
        aes = cipher.decryptor()
        return self._strip_padding(aes.update(encrypted_data) + aes.finalize())

    def _strip_padding(self, decrypted):
        padding_size = ord(decrypted[-1:])
        if padding_size >= 16:
            return decrypted
        else:
            return decrypted[:-padding_size]

    def _derive_pbkdf2(self, password):
        kdf = PBKDF2HMAC(
            algorithm=SHA1(),
            length=32,
            salt=self._encrypted_key.salt,
            iterations=self.iterations,
            backend=_backend)

        key_and_iv = kdf.derive(password)
        return (
            key_and_iv[:16],
            key_and_iv[16:],
        )

    def _derive_openssl(self, key, salt):
        key = key[:-16]
        key_and_iv = b""
        prev = b""
        while len(key_and_iv) < 32:
            prev = md5(prev + key + salt).digest()
            key_and_iv += prev
        return (
            key_and_iv[:16],
            key_and_iv[16:],
        )
