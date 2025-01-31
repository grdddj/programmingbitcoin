import hashlib
import hmac
from io import BytesIO
from random import randint
from typing import Union
from unittest import TestCase

from .helper import encode_base58_checksum, hash160


class FieldElement:
    def __init__(self, num: int, prime: int) -> None:
        if num >= prime or num < 0:
            error = f"Num {num} not in field range 0 to {prime - 1}"
            raise ValueError(error)
        self.num = num
        self.prime = prime

    def __repr__(self) -> str:
        return f"FieldElement_{self.prime}({self.num})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FieldElement):
            raise NotImplementedError
        if other is None:
            return False
        return self.num == other.num and self.prime == other.prime

    def __ne__(self, other: object) -> bool:
        if not isinstance(other, FieldElement):
            raise NotImplementedError
        # this should be the inverse of the == operator
        return not (self == other)

    def __add__(self, other: "FieldElement") -> "FieldElement":
        if self.prime != other.prime:
            raise TypeError("Cannot add two numbers in different Fields")
        # self.num and other.num are the actual values
        # self.prime is what we need to mod against
        num = (self.num + other.num) % self.prime
        # We return an element of the same class
        return self.__class__(num, self.prime)

    def __sub__(self, other: "FieldElement") -> "FieldElement":
        if self.prime != other.prime:
            raise TypeError("Cannot subtract two numbers in different Fields")
        # self.num and other.num are the actual values
        # self.prime is what we need to mod against
        num = (self.num - other.num) % self.prime
        # We return an element of the same class
        return self.__class__(num, self.prime)

    def __mul__(self, other: "FieldElement") -> "FieldElement":
        if self.prime != other.prime:
            raise TypeError("Cannot multiply two numbers in different Fields")
        # self.num and other.num are the actual values
        # self.prime is what we need to mod against
        num = (self.num * other.num) % self.prime
        # We return an element of the same class
        return self.__class__(num, self.prime)

    def __pow__(self, exponent: int) -> "FieldElement":
        n = exponent % (self.prime - 1)
        num = pow(self.num, n, self.prime)
        return self.__class__(num, self.prime)

    def __truediv__(self, other: "FieldElement") -> "FieldElement":
        if self.prime != other.prime:
            raise TypeError("Cannot divide two numbers in different Fields")
        # self.num and other.num are the actual values
        # self.prime is what we need to mod against
        # use fermat's little theorem:
        # self.num**(p-1) % p == 1
        # this means:
        # 1/n == pow(n, p-2, p)
        num = (self.num * pow(other.num, self.prime - 2, self.prime)) % self.prime
        # We return an element of the same class
        return self.__class__(num, self.prime)

    def __rmul__(self, coefficient: int) -> "FieldElement":
        num = (self.num * coefficient) % self.prime
        return self.__class__(num=num, prime=self.prime)


class FieldElementTest(TestCase):
    def test_ne(self):
        a = FieldElement(2, 31)
        b = FieldElement(2, 31)
        c = FieldElement(15, 31)
        self.assertEqual(a, b)
        self.assertTrue(a != c)
        self.assertFalse(a != b)

    def test_add(self):
        a = FieldElement(2, 31)
        b = FieldElement(15, 31)
        self.assertEqual(a + b, FieldElement(17, 31))
        a = FieldElement(17, 31)
        b = FieldElement(21, 31)
        self.assertEqual(a + b, FieldElement(7, 31))

    def test_sub(self):
        a = FieldElement(29, 31)
        b = FieldElement(4, 31)
        self.assertEqual(a - b, FieldElement(25, 31))
        a = FieldElement(15, 31)
        b = FieldElement(30, 31)
        self.assertEqual(a - b, FieldElement(16, 31))

    def test_mul(self):
        a = FieldElement(24, 31)
        b = FieldElement(19, 31)
        self.assertEqual(a * b, FieldElement(22, 31))

    def test_rmul(self):
        a = FieldElement(24, 31)
        b = 2
        self.assertEqual(b * a, a + a)

    def test_pow(self):
        a = FieldElement(17, 31)
        self.assertEqual(a ** 3, FieldElement(15, 31))
        a = FieldElement(5, 31)
        b = FieldElement(18, 31)
        self.assertEqual(a ** 5 * b, FieldElement(16, 31))

    def test_div(self):
        a = FieldElement(3, 31)
        b = FieldElement(24, 31)
        self.assertEqual(a / b, FieldElement(4, 31))
        a = FieldElement(17, 31)
        self.assertEqual(a ** -3, FieldElement(29, 31))
        a = FieldElement(4, 31)
        b = FieldElement(11, 31)
        self.assertEqual(a ** -4 * b, FieldElement(13, 31))


class Point:
    def __init__(
        self,
        x: Union[int, FieldElement, None],
        y: Union[int, FieldElement, None],
        a: int,
        b: int,
    ) -> None:
        self.a = a
        self.b = b
        self.x = x
        self.y = y
        # x being None and y being None represents the point at infinity
        # Check for that here since the equation below won't make sense
        # with None values for both.
        if self.x is None and self.y is None:
            return
        assert self.x is not None and self.y is not None
        # make sure that the elliptic curve equation is satisfied
        # y**2 == x**3 + a*x + b
        if self.y ** 2 != self.x ** 3 + a * self.x + b:
            # if not, throw a ValueError
            raise ValueError(f"({x}, {y}) is not on the curve")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Point):
            raise NotImplementedError
        return (
            self.x == other.x
            and self.y == other.y
            and self.a == other.a
            and self.b == other.b
        )

    def __ne__(self, other: object) -> bool:
        if not isinstance(other, Point):
            raise NotImplementedError
        # this should be the inverse of the == operator
        return not (self == other)

    def __repr__(self) -> str:
        if self.x is None:
            return "Point(infinity)"
        elif isinstance(self.x, FieldElement):
            assert (
                isinstance(self.y, FieldElement)
                and isinstance(self.a, FieldElement)
                and isinstance(self.b, FieldElement)
            )
            return f"Point({self.x.num},{self.y.num})_{self.a.num}_{self.b.num} FieldElement({self.x.prime})"
        else:
            return f"Point({self.x},{self.y})_{self.a}_{self.b}"

    def __add__(self, other: "Point") -> "Point":
        if self.a != other.a or self.b != other.b:
            raise TypeError(f"Points {self}, {other} are not on the same curve")
        # Case 0.0: self is the point at infinity, return other
        if self.x is None:
            return other
        # Case 0.1: other is the point at infinity, return self
        if other.x is None:
            return self

        # Case 1: self.x == other.x, self.y != other.y
        # Result is point at infinity
        if self.x == other.x and self.y != other.y:
            return self.__class__(None, None, self.a, self.b)

        # Case 2: self.x ≠ other.x
        # Formula (x3,y3)==(x1,y1)+(x2,y2)
        # s=(y2-y1)/(x2-x1)
        # x3=s**2-x1-x2
        # y3=s*(x1-x3)-y1
        if self.x != other.x:
            s = (other.y - self.y) / (other.x - self.x)
            x = s ** 2 - self.x - other.x
            y = s * (self.x - x) - self.y
            return self.__class__(x, y, self.a, self.b)

        # Case 4: if we are tangent to the vertical line,
        # we return the point at infinity
        # note instead of figuring out what 0 is for each type
        # we just use 0 * self.x
        if self == other and self.y == 0 * self.x:
            return self.__class__(None, None, self.a, self.b)

        # Case 3: self == other
        # Formula (x3,y3)=(x1,y1)+(x1,y1)
        # s=(3*x1**2+a)/(2*y1)
        # x3=s**2-2*x1
        # y3=s*(x1-x3)-y1
        if self == other:
            s = (3 * self.x ** 2 + self.a) / (2 * self.y)
            x = s ** 2 - 2 * self.x
            y = s * (self.x - x) - self.y
            return self.__class__(x, y, self.a, self.b)

        raise ValueError("No scenario matched")

    def __rmul__(self, coefficient: int) -> "Point":
        coef = coefficient
        current = self
        result = self.__class__(None, None, self.a, self.b)
        while coef:
            if coef & 1:
                result += current
            current += current
            coef >>= 1
        return result


class PointTest(TestCase):
    def test_ne(self):
        a = Point(x=3, y=-7, a=5, b=7)
        b = Point(x=18, y=77, a=5, b=7)
        self.assertTrue(a != b)
        self.assertFalse(a != a)

    def test_on_curve(self):
        with self.assertRaises(ValueError):
            Point(x=-2, y=4, a=5, b=7)
        # these should not raise an error
        Point(x=3, y=-7, a=5, b=7)
        Point(x=18, y=77, a=5, b=7)

    def test_add0(self):
        a = Point(x=None, y=None, a=5, b=7)
        b = Point(x=2, y=5, a=5, b=7)
        c = Point(x=2, y=-5, a=5, b=7)
        self.assertEqual(a + b, b)
        self.assertEqual(b + a, b)
        self.assertEqual(b + c, a)

    def test_add1(self):
        a = Point(x=3, y=7, a=5, b=7)
        b = Point(x=-1, y=-1, a=5, b=7)
        self.assertEqual(a + b, Point(x=2, y=-5, a=5, b=7))

    def test_add2(self):
        a = Point(x=-1, y=1, a=5, b=7)
        self.assertEqual(a + a, Point(x=18, y=-77, a=5, b=7))


class ECCTest(TestCase):
    def test_on_curve(self):
        # tests the following points whether they are on the curve or not
        # on curve y^2=x^3-7 over F_223:
        # (192,105) (17,56) (200,119) (1,193) (42,99)
        # the ones that aren't should raise a ValueError
        prime = 223
        a = FieldElement(0, prime)
        b = FieldElement(7, prime)

        valid_points = ((192, 105), (17, 56), (1, 193))
        invalid_points = ((200, 119), (42, 99))

        # iterate over valid points
        for x_raw, y_raw in valid_points:
            x = FieldElement(x_raw, prime)
            y = FieldElement(y_raw, prime)
            # Creating the point should not result in an error
            Point(x, y, a, b)

        # iterate over invalid points
        for x_raw, y_raw in invalid_points:
            x = FieldElement(x_raw, prime)
            y = FieldElement(y_raw, prime)
            with self.assertRaises(ValueError):
                Point(x, y, a, b)

    def test_add(self):
        # tests the following additions on curve y^2=x^3-7 over F_223:
        # (192,105) + (17,56)
        # (47,71) + (117,141)
        # (143,98) + (76,66)
        prime = 223
        a = FieldElement(0, prime)
        b = FieldElement(7, prime)

        additions = (
            # (x1, y1, x2, y2, x3, y3)
            (192, 105, 17, 56, 170, 142),
            (47, 71, 117, 141, 60, 139),
            (143, 98, 76, 66, 47, 71),
        )
        # iterate over the additions
        for x1_raw, y1_raw, x2_raw, y2_raw, x3_raw, y3_raw in additions:
            x1 = FieldElement(x1_raw, prime)
            y1 = FieldElement(y1_raw, prime)
            p1 = Point(x1, y1, a, b)
            x2 = FieldElement(x2_raw, prime)
            y2 = FieldElement(y2_raw, prime)
            p2 = Point(x2, y2, a, b)
            x3 = FieldElement(x3_raw, prime)
            y3 = FieldElement(y3_raw, prime)
            p3 = Point(x3, y3, a, b)
            # check that p1 + p2 == p3
            self.assertEqual(p1 + p2, p3)

    def test_rmul(self):
        # tests the following scalar multiplications
        # 2*(192,105)
        # 2*(143,98)
        # 2*(47,71)
        # 4*(47,71)
        # 8*(47,71)
        # 21*(47,71)
        prime = 223
        a = FieldElement(0, prime)
        b = FieldElement(7, prime)

        multiplications = (
            # (coefficient, x1, y1, x2, y2)
            (2, 192, 105, 49, 71),
            (2, 143, 98, 64, 168),
            (2, 47, 71, 36, 111),
            (4, 47, 71, 194, 51),
            (8, 47, 71, 116, 55),
            (21, 47, 71, None, None),
        )

        # iterate over the multiplications
        for s, x1_raw, y1_raw, x2_raw, y2_raw in multiplications:
            x1 = FieldElement(x1_raw, prime)
            y1 = FieldElement(y1_raw, prime)
            p1 = Point(x1, y1, a, b)
            # initialize the second point based on whether it's the point at infinity
            if x2_raw is None:
                p2 = Point(None, None, a, b)
            else:
                x2 = FieldElement(x2_raw, prime)
                y2 = FieldElement(y2_raw, prime)
                p2 = Point(x2, y2, a, b)

            # check that the product is equal to the expected point
            self.assertEqual(s * p1, p2)


A = 0
B = 7
P = 2 ** 256 - 2 ** 32 - 977
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141


class S256Field(FieldElement):
    def __init__(self, num: int, prime: int = None) -> None:
        super().__init__(num=num, prime=P)

    def __repr__(self) -> str:
        return f"{self.num:x}".zfill(64)

    def sqrt(self) -> "S256Field":
        return self ** ((P + 1) // 4)


class S256Point(Point):
    def __init__(
        self,
        x: Union[int, FieldElement, None],
        y: Union[int, FieldElement, None],
        a=None,
        b=None,
    ) -> None:
        a, b = S256Field(A), S256Field(B)
        if isinstance(x, int):
            super().__init__(x=S256Field(x), y=S256Field(y), a=a, b=b)
        else:
            super().__init__(x=x, y=y, a=a, b=b)

    def __repr__(self) -> str:
        if self.x is None:
            return "S256Point(infinity)"
        else:
            return f"S256Point({self.x}, {self.y})"

    def __rmul__(self, coefficient: int) -> "Point":
        coef = coefficient % N
        return super().__rmul__(coef)

    def verify(self, z: int, sig: "Signature") -> bool:
        # By Fermat's Little Theorem, 1/s = pow(s, N-2, N)
        s_inv = pow(sig.s, N - 2, N)
        # u = z / s
        u = z * s_inv % N
        # v = r / s
        v = sig.r * s_inv % N
        # u*G + v*P should have as the x coordinate, r
        total = u * G + v * self
        return total.x.num == sig.r

    def sec(self, compressed: bool = True) -> bytes:
        """returns the binary version of the SEC format"""
        # if compressed, starts with b'\x02' if self.y.num is even, b'\x03' if self.y is odd
        # then self.x.num
        # remember, you have to convert self.x.num/self.y.num to binary (some_integer.to_bytes(32, 'big'))
        if compressed:
            if self.y.num % 2 == 0:
                return b"\x02" + self.x.num.to_bytes(32, "big")
            else:
                return b"\x03" + self.x.num.to_bytes(32, "big")
        else:
            # if non-compressed, starts with b'\x04' followod by self.x and then self.y
            return (
                b"\x04"
                + self.x.num.to_bytes(32, "big")
                + self.y.num.to_bytes(32, "big")
            )

    def hash160(self, compressed: bool = True) -> bytes:
        return hash160(self.sec(compressed))

    def address(self, compressed: bool = True, testnet: bool = False) -> str:
        """Returns the address string"""
        h160 = self.hash160(compressed)
        if testnet:
            prefix = b"\x6f"
        else:
            prefix = b"\x00"
        return encode_base58_checksum(prefix + h160)

    @classmethod
    def parse(cls, sec_bin: bytes) -> "S256Point":
        """returns a Point object from a SEC binary (not hex)"""
        if sec_bin[0] == 4:
            x = int.from_bytes(sec_bin[1:33], "big")
            y = int.from_bytes(sec_bin[33:65], "big")
            return S256Point(x=x, y=y)
        is_even = sec_bin[0] == 2
        x = S256Field(int.from_bytes(sec_bin[1:], "big"))
        # right side of the equation y^2 = x^3 + 7
        alpha = x ** 3 + S256Field(B)
        # solve for left side
        beta = alpha.sqrt()
        if beta.num % 2 == 0:
            even_beta = beta
            odd_beta = S256Field(P - beta.num)
        else:
            even_beta = S256Field(P - beta.num)
            odd_beta = beta
        if is_even:
            return S256Point(x, even_beta)
        else:
            return S256Point(x, odd_beta)


G = S256Point(
    0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
    0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8,
)


class S256Test(TestCase):
    def test_order(self):
        point = N * G
        self.assertIsNone(point.x)

    def test_pubpoint(self):
        # write a test that tests the public point for the following
        points = (
            # secret, x, y
            (
                7,
                0x5CBDF0646E5DB4EAA398F365F2EA7A0E3D419B7E0330E39CE92BDDEDCAC4F9BC,
                0x6AEBCA40BA255960A3178D6D861A54DBA813D0B813FDE7B5A5082628087264DA,
            ),
            (
                1485,
                0xC982196A7466FBBBB0E27A940B6AF926C1A74D5AD07128C82824A11B5398AFDA,
                0x7A91F9EAE64438AFB9CE6448A1C133DB2D8FB9254E4546B6F001637D50901F55,
            ),
            (
                2 ** 128,
                0x8F68B9D2F63B5F339239C1AD981F162EE88C5678723EA3351B7B444C9EC4C0DA,
                0x662A9F2DBA063986DE1D90C2B6BE215DBBEA2CFE95510BFDF23CBF79501FFF82,
            ),
            (
                2 ** 240 + 2 ** 31,
                0x9577FF57C8234558F293DF502CA4F09CBC65A6572C842B39B366F21717945116,
                0x10B49C67FA9365AD7B90DAB070BE339A1DAF9052373EC30FFAE4F72D5E66D053,
            ),
        )

        # iterate over points
        for secret, x, y in points:
            # initialize the secp256k1 point (S256Point)
            point = S256Point(x, y)
            # check that the secret*G is the same as the point
            self.assertEqual(secret * G, point)

    def test_verify(self):
        point = S256Point(
            0x887387E452B8EACC4ACFDE10D9AAF7F6D9A0F975AABB10D006E4DA568744D06C,
            0x61DE6D95231CD89026E286DF3B6AE4A894A3378E393E93A0F45B666329A0AE34,
        )
        z = 0xEC208BAA0FC1C19F708A9CA96FDEFF3AC3F230BB4A7BA4AEDE4942AD003C0F60
        r = 0xAC8D1C87E51D0D441BE8B3DD5B05C8795B48875DFFE00B7FFCFAC23010D3A395
        s = 0x68342CEFF8935EDEDD102DD876FFD6BA72D6A427A3EDB13D26EB0781CB423C4
        self.assertTrue(point.verify(z, Signature(r, s)))
        z = 0x7C076FF316692A3D7EB3C3BB0F8B1488CF72E1AFCD929E29307032997A838A3D
        r = 0xEFF69EF2B1BD93A66ED5219ADD4FB51E11A840F404876325A1E8FFE0529A2C
        s = 0xC7207FEE197D27C618AEA621406F6BF5EF6FCA38681D82B2F06FDDBDCE6FEAB6
        self.assertTrue(point.verify(z, Signature(r, s)))

    def test_sec(self):
        coefficient = 999 ** 3
        uncompressed = "049d5ca49670cbe4c3bfa84c96a8c87df086c6ea6a24ba6b809c9de234496808d56fa15cc7f3d38cda98dee2419f415b7513dde1301f8643cd9245aea7f3f911f9"
        compressed = (
            "039d5ca49670cbe4c3bfa84c96a8c87df086c6ea6a24ba6b809c9de234496808d5"
        )
        point = coefficient * G
        self.assertEqual(point.sec(compressed=False), bytes.fromhex(uncompressed))
        self.assertEqual(point.sec(compressed=True), bytes.fromhex(compressed))
        coefficient = 123
        uncompressed = "04a598a8030da6d86c6bc7f2f5144ea549d28211ea58faa70ebf4c1e665c1fe9b5204b5d6f84822c307e4b4a7140737aec23fc63b65b35f86a10026dbd2d864e6b"
        compressed = (
            "03a598a8030da6d86c6bc7f2f5144ea549d28211ea58faa70ebf4c1e665c1fe9b5"
        )
        point = coefficient * G
        self.assertEqual(point.sec(compressed=False), bytes.fromhex(uncompressed))
        self.assertEqual(point.sec(compressed=True), bytes.fromhex(compressed))
        coefficient = 42424242
        uncompressed = "04aee2e7d843f7430097859e2bc603abcc3274ff8169c1a469fee0f20614066f8e21ec53f40efac47ac1c5211b2123527e0e9b57ede790c4da1e72c91fb7da54a3"
        compressed = (
            "03aee2e7d843f7430097859e2bc603abcc3274ff8169c1a469fee0f20614066f8e"
        )
        point = coefficient * G
        self.assertEqual(point.sec(compressed=False), bytes.fromhex(uncompressed))
        self.assertEqual(point.sec(compressed=True), bytes.fromhex(compressed))

    def test_address(self):
        secret = 888 ** 3
        mainnet_address = "148dY81A9BmdpMhvYEVznrM45kWN32vSCN"
        testnet_address = "mieaqB68xDCtbUBYFoUNcmZNwk74xcBfTP"
        point = secret * G
        self.assertEqual(point.address(compressed=True, testnet=False), mainnet_address)
        self.assertEqual(point.address(compressed=True, testnet=True), testnet_address)
        secret = 321
        mainnet_address = "1S6g2xBJSED7Qr9CYZib5f4PYVhHZiVfj"
        testnet_address = "mfx3y63A7TfTtXKkv7Y6QzsPFY6QCBCXiP"
        point = secret * G
        self.assertEqual(
            point.address(compressed=False, testnet=False), mainnet_address
        )
        self.assertEqual(point.address(compressed=False, testnet=True), testnet_address)
        secret = 4242424242
        mainnet_address = "1226JSptcStqn4Yq9aAmNXdwdc2ixuH9nb"
        testnet_address = "mgY3bVusRUL6ZB2Ss999CSrGVbdRwVpM8s"
        point = secret * G
        self.assertEqual(
            point.address(compressed=False, testnet=False), mainnet_address
        )
        self.assertEqual(point.address(compressed=False, testnet=True), testnet_address)


class Signature:
    def __init__(self, r: int, s: int) -> None:
        self.r = r
        self.s = s

    def __repr__(self) -> str:
        return f"Signature({self.r:x},{self.s:x})"

    def der(self) -> bytes:
        rbin = self.r.to_bytes(32, byteorder="big")
        # remove all null bytes at the beginning
        rbin = rbin.lstrip(b"\x00")
        # if rbin has a high bit, add a \x00
        if rbin[0] & 0x80:
            rbin = b"\x00" + rbin
        result = bytes([2, len(rbin)]) + rbin
        sbin = self.s.to_bytes(32, byteorder="big")
        # remove all null bytes at the beginning
        sbin = sbin.lstrip(b"\x00")
        # if sbin has a high bit, add a \x00
        if sbin[0] & 0x80:
            sbin = b"\x00" + sbin
        result += bytes([2, len(sbin)]) + sbin
        return bytes([0x30, len(result)]) + result

    @classmethod
    def parse(cls, signature_bin: bytes) -> "Signature":
        s = BytesIO(signature_bin)
        compound = s.read(1)[0]
        if compound != 0x30:
            raise SyntaxError("Bad Signature")
        length = s.read(1)[0]
        if length + 2 != len(signature_bin):
            raise SyntaxError("Bad Signature Length")
        marker = s.read(1)[0]
        if marker != 0x02:
            raise SyntaxError("Bad Signature")
        rlength = s.read(1)[0]
        r = int.from_bytes(s.read(rlength), "big")
        marker = s.read(1)[0]
        if marker != 0x02:
            raise SyntaxError("Bad Signature")
        slength = s.read(1)[0]
        s = int.from_bytes(s.read(slength), "big")
        if len(signature_bin) != 6 + rlength + slength:
            raise SyntaxError("Signature too long")
        return cls(r, s)


class SignatureTest(TestCase):
    def test_der(self):
        testcases = (
            (1, 2),
            (randint(0, 2 ** 256), randint(0, 2 ** 255)),
            (randint(0, 2 ** 256), randint(0, 2 ** 255)),
        )
        for r, s in testcases:
            sig = Signature(r, s)
            der = sig.der()
            sig2 = Signature.parse(der)
            self.assertEqual(sig2.r, r)
            self.assertEqual(sig2.s, s)


class PrivateKey:
    def __init__(self, secret: int) -> None:
        self.secret = secret
        self.point: S256Point = secret * G

    def hex(self) -> str:
        return f"{self.secret:x}".zfill(64)

    def sign(self, z: int) -> Signature:
        k = self.deterministic_k(z)
        # r is the x coordinate of the resulting point k*G
        r = (k * G).x.num
        # remember 1/k = pow(k, N-2, N)
        k_inv = pow(k, N - 2, N)
        # s = (z+r*secret) / k
        s = (z + r * self.secret) * k_inv % N
        if s > N / 2:
            s = N - s
        # return an instance of Signature:
        # Signature(r, s)
        return Signature(r, s)

    def deterministic_k(self, z: int) -> int:
        k = b"\x00" * 32
        v = b"\x01" * 32
        if z > N:
            z -= N
        z_bytes = z.to_bytes(32, "big")
        secret_bytes = self.secret.to_bytes(32, "big")
        s256 = hashlib.sha256
        k = hmac.new(k, v + b"\x00" + secret_bytes + z_bytes, s256).digest()
        v = hmac.new(k, v, s256).digest()
        k = hmac.new(k, v + b"\x01" + secret_bytes + z_bytes, s256).digest()
        v = hmac.new(k, v, s256).digest()
        while True:
            v = hmac.new(k, v, s256).digest()
            candidate = int.from_bytes(v, "big")
            if candidate >= 1 and candidate < N:
                return candidate
            k = hmac.new(k, v + b"\x00", s256).digest()
            v = hmac.new(k, v, s256).digest()

    def wif(self, compressed: bool = True, testnet: bool = False) -> str:
        # convert the secret from integer to a 32-bytes in big endian using num.to_bytes(32, 'big')
        secret_bytes = self.secret.to_bytes(32, "big")
        # prepend b'\xef' on testnet, b'\x80' on mainnet
        if testnet:
            prefix = b"\xef"
        else:
            prefix = b"\x80"
        # append b'\x01' if compressed
        if compressed:
            suffix = b"\x01"
        else:
            suffix = b""
        # encode_base58_checksum the whole thing
        return encode_base58_checksum(prefix + secret_bytes + suffix)


class PrivateKeyTest(TestCase):
    def test_sign(self):
        pk = PrivateKey(randint(0, N))
        z = randint(0, 2 ** 256)
        sig = pk.sign(z)
        self.assertTrue(pk.point.verify(z, sig))

    def test_wif(self):
        pk = PrivateKey(2 ** 256 - 2 ** 199)
        expected = "L5oLkpV3aqBJ4BgssVAsax1iRa77G5CVYnv9adQ6Z87te7TyUdSC"
        self.assertEqual(pk.wif(compressed=True, testnet=False), expected)
        pk = PrivateKey(2 ** 256 - 2 ** 201)
        expected = "93XfLeifX7Jx7n7ELGMAf1SUR6f9kgQs8Xke8WStMwUtrDucMzn"
        self.assertEqual(pk.wif(compressed=False, testnet=True), expected)
        pk = PrivateKey(
            0x0DBA685B4511DBD3D368E5C4358A1277DE9486447AF7B3604A69B8D9D8B7889D
        )
        expected = "5HvLFPDVgFZRK9cd4C5jcWki5Skz6fmKqi1GQJf5ZoMofid2Dty"
        self.assertEqual(pk.wif(compressed=False, testnet=False), expected)
        pk = PrivateKey(
            0x1CCA23DE92FD1862FB5B76E5F4F50EB082165E5191E116C18ED1A6B24BE6A53F
        )
        expected = "cNYfWuhDpbNM1JWc3c6JTrtrFVxU4AGhUKgw5f93NP2QaBqmxKkg"
        self.assertEqual(pk.wif(compressed=True, testnet=True), expected)
