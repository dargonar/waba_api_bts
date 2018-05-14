from bitsharesbase.account import BrainKey, Address, PublicKey, PrivateKey
# from bitsharesbase.memo import (
#     get_shared_secret,
#     _pad,
#     _unpad,
#     encode_memo,
#     decode_memo
# )
import my_memo
dec = my_memo.decode_memo(PrivateKey('5JQGCnJCDyraociQmhDRDxzNFCd8WdcJ4BAj8q1YDZtVpk5NDw9'),
                              PublicKey('BTS6ewtnzaP7JEGs5RnQtkyG6ESaDHtLJTP6zrgViHBFTDxq2n66Q', prefix="BTS"),
                              0,
                              '7505b97933b143eadddfda7ba2f92c14')

print (dec)

