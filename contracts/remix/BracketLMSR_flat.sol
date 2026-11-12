// SPDX-License-Identifier: MIT
// FLATTENED by scripts/compile.js from BracketLMSR.sol. Do not edit. Edit the source and re-run.
// Bundled libraries keep their own licences: ABDKMath64x64 (BSD-4-Clause, ABDK Consulting),
// OpenZeppelin Contracts 4.9.6 ReentrancyGuard (MIT).
pragma solidity ^0.8.20;

// ---- begin abdk-libraries-solidity/ABDKMath64x64.sol ----
/*
 * ABDK Math 64.64 Smart Contract Library.  Copyright © 2019 by ABDK Consulting.
 * Author: Mikhail Vladimirov <mikhail.vladimirov@gmail.com>
 */

/**
 * Smart contract library of mathematical functions operating with signed
 * 64.64-bit fixed point numbers.  Signed 64.64-bit fixed point number is
 * basically a simple fraction whose numerator is signed 128-bit integer and
 * denominator is 2^64.  As long as denominator is always the same, there is no
 * need to store it, thus in Solidity signed 64.64-bit fixed point numbers are
 * represented by int128 type holding only the numerator.
 */
library ABDKMath64x64 {
  /*
   * Minimum value signed 64.64-bit fixed point number may have. 
   */
  int128 private constant MIN_64x64 = -0x80000000000000000000000000000000;

  /*
   * Maximum value signed 64.64-bit fixed point number may have. 
   */
  int128 private constant MAX_64x64 = 0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF;

  /**
   * Convert signed 256-bit integer number into signed 64.64-bit fixed point
   * number.  Revert on overflow.
   *
   * @param x signed 256-bit integer number
   * @return signed 64.64-bit fixed point number
   */
  function fromInt (int256 x) internal pure returns (int128) {
    unchecked {
      require (x >= -0x8000000000000000 && x <= 0x7FFFFFFFFFFFFFFF);
      return int128 (x << 64);
    }
  }

  /**
   * Convert signed 64.64 fixed point number into signed 64-bit integer number
   * rounding down.
   *
   * @param x signed 64.64-bit fixed point number
   * @return signed 64-bit integer number
   */
  function toInt (int128 x) internal pure returns (int64) {
    unchecked {
      return int64 (x >> 64);
    }
  }

  /**
   * Convert unsigned 256-bit integer number into signed 64.64-bit fixed point
   * number.  Revert on overflow.
   *
   * @param x unsigned 256-bit integer number
   * @return signed 64.64-bit fixed point number
   */
  function fromUInt (uint256 x) internal pure returns (int128) {
    unchecked {
      require (x <= 0x7FFFFFFFFFFFFFFF);
      return int128 (int256 (x << 64));
    }
  }

  /**
   * Convert signed 64.64 fixed point number into unsigned 64-bit integer
   * number rounding down.  Revert on underflow.
   *
   * @param x signed 64.64-bit fixed point number
   * @return unsigned 64-bit integer number
   */
  function toUInt (int128 x) internal pure returns (uint64) {
    unchecked {
      require (x >= 0);
      return uint64 (uint128 (x >> 64));
    }
  }

  /**
   * Convert signed 128.128 fixed point number into signed 64.64-bit fixed point
   * number rounding down.  Revert on overflow.
   *
   * @param x signed 128.128-bin fixed point number
   * @return signed 64.64-bit fixed point number
   */
  function from128x128 (int256 x) internal pure returns (int128) {
    unchecked {
      int256 result = x >> 64;
      require (result >= MIN_64x64 && result <= MAX_64x64);
      return int128 (result);
    }
  }

  /**
   * Convert signed 64.64 fixed point number into signed 128.128 fixed point
   * number.
   *
   * @param x signed 64.64-bit fixed point number
   * @return signed 128.128 fixed point number
   */
  function to128x128 (int128 x) internal pure returns (int256) {
    unchecked {
      return int256 (x) << 64;
    }
  }

  /**
   * Calculate x + y.  Revert on overflow.
   *
   * @param x signed 64.64-bit fixed point number
   * @param y signed 64.64-bit fixed point number
   * @return signed 64.64-bit fixed point number
   */
  function add (int128 x, int128 y) internal pure returns (int128) {
    unchecked {
      int256 result = int256(x) + y;
      require (result >= MIN_64x64 && result <= MAX_64x64);
      return int128 (result);
    }
  }

  /**
   * Calculate x - y.  Revert on overflow.
   *
   * @param x signed 64.64-bit fixed point number
   * @param y signed 64.64-bit fixed point number
   * @return signed 64.64-bit fixed point number
   */
  function sub (int128 x, int128 y) internal pure returns (int128) {
    unchecked {
      int256 result = int256(x) - y;
      require (result >= MIN_64x64 && result <= MAX_64x64);
      return int128 (result);
    }
  }

  /**
   * Calculate x * y rounding down.  Revert on overflow.
   *
   * @param x signed 64.64-bit fixed point number
   * @param y signed 64.64-bit fixed point number
   * @return signed 64.64-bit fixed point number
   */
  function mul (int128 x, int128 y) internal pure returns (int128) {
    unchecked {
      int256 result = int256(x) * y >> 64;
      require (result >= MIN_64x64 && result <= MAX_64x64);
      return int128 (result);
    }
  }

  /**
   * Calculate x * y rounding towards zero, where x is signed 64.64 fixed point
   * number and y is signed 256-bit integer number.  Revert on overflow.
   *
   * @param x signed 64.64 fixed point number
   * @param y signed 256-bit integer number
   * @return signed 256-bit integer number
   */
  function muli (int128 x, int256 y) internal pure returns (int256) {
    unchecked {
      if (x == MIN_64x64) {
        require (y >= -0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF &&
          y <= 0x1000000000000000000000000000000000000000000000000);
        return -y << 63;
      } else {
        bool negativeResult = false;
        if (x < 0) {
          x = -x;
          negativeResult = true;
        }
        if (y < 0) {
          y = -y; // We rely on overflow behavior here
          negativeResult = !negativeResult;
        }
        uint256 absoluteResult = mulu (x, uint256 (y));
        if (negativeResult) {
          require (absoluteResult <=
            0x8000000000000000000000000000000000000000000000000000000000000000);
          return -int256 (absoluteResult); // We rely on overflow behavior here
        } else {
          require (absoluteResult <=
            0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF);
          return int256 (absoluteResult);
        }
      }
    }
  }

  /**
   * Calculate x * y rounding down, where x is signed 64.64 fixed point number
   * and y is unsigned 256-bit integer number.  Revert on overflow.
   *
   * @param x signed 64.64 fixed point number
   * @param y unsigned 256-bit integer number
   * @return unsigned 256-bit integer number
   */
  function mulu (int128 x, uint256 y) internal pure returns (uint256) {
    unchecked {
      if (y == 0) return 0;

      require (x >= 0);

      uint256 lo = (uint256 (int256 (x)) * (y & 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF)) >> 64;
      uint256 hi = uint256 (int256 (x)) * (y >> 128);

      require (hi <= 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF);
      hi <<= 64;

      require (hi <=
        0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF - lo);
      return hi + lo;
    }
  }

  /**
   * Calculate x / y rounding towards zero.  Revert on overflow or when y is
   * zero.
   *
   * @param x signed 64.64-bit fixed point number
   * @param y signed 64.64-bit fixed point number
   * @return signed 64.64-bit fixed point number
   */
  function div (int128 x, int128 y) internal pure returns (int128) {
    unchecked {
      require (y != 0);
      int256 result = (int256 (x) << 64) / y;
      require (result >= MIN_64x64 && result <= MAX_64x64);
      return int128 (result);
    }
  }

  /**
   * Calculate x / y rounding towards zero, where x and y are signed 256-bit
   * integer numbers.  Revert on overflow or when y is zero.
   *
   * @param x signed 256-bit integer number
   * @param y signed 256-bit integer number
   * @return signed 64.64-bit fixed point number
   */
  function divi (int256 x, int256 y) internal pure returns (int128) {
    unchecked {
      require (y != 0);

      bool negativeResult = false;
      if (x < 0) {
        x = -x; // We rely on overflow behavior here
        negativeResult = true;
      }
      if (y < 0) {
        y = -y; // We rely on overflow behavior here
        negativeResult = !negativeResult;
      }
      uint128 absoluteResult = divuu (uint256 (x), uint256 (y));
      if (negativeResult) {
        require (absoluteResult <= 0x80000000000000000000000000000000);
        return -int128 (absoluteResult); // We rely on overflow behavior here
      } else {
        require (absoluteResult <= 0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF);
        return int128 (absoluteResult); // We rely on overflow behavior here
      }
    }
  }

  /**
   * Calculate x / y rounding towards zero, where x and y are unsigned 256-bit
   * integer numbers.  Revert on overflow or when y is zero.
   *
   * @param x unsigned 256-bit integer number
   * @param y unsigned 256-bit integer number
   * @return signed 64.64-bit fixed point number
   */
  function divu (uint256 x, uint256 y) internal pure returns (int128) {
    unchecked {
      require (y != 0);
      uint128 result = divuu (x, y);
      require (result <= uint128 (MAX_64x64));
      return int128 (result);
    }
  }

  /**
   * Calculate -x.  Revert on overflow.
   *
   * @param x signed 64.64-bit fixed point number
   * @return signed 64.64-bit fixed point number
   */
  function neg (int128 x) internal pure returns (int128) {
    unchecked {
      require (x != MIN_64x64);
      return -x;
    }
  }

  /**
   * Calculate |x|.  Revert on overflow.
   *
   * @param x signed 64.64-bit fixed point number
   * @return signed 64.64-bit fixed point number
   */
  function abs (int128 x) internal pure returns (int128) {
    unchecked {
      require (x != MIN_64x64);
      return x < 0 ? -x : x;
    }
  }

  /**
   * Calculate 1 / x rounding towards zero.  Revert on overflow or when x is
   * zero.
   *
   * @param x signed 64.64-bit fixed point number
   * @return signed 64.64-bit fixed point number
   */
  function inv (int128 x) internal pure returns (int128) {
    unchecked {
      require (x != 0);
      int256 result = int256 (0x100000000000000000000000000000000) / x;
      require (result >= MIN_64x64 && result <= MAX_64x64);
      return int128 (result);
    }
  }

  /**
   * Calculate arithmetics average of x and y, i.e. (x + y) / 2 rounding down.
   *
   * @param x signed 64.64-bit fixed point number
   * @param y signed 64.64-bit fixed point number
   * @return signed 64.64-bit fixed point number
   */
  function avg (int128 x, int128 y) internal pure returns (int128) {
    unchecked {
      return int128 ((int256 (x) + int256 (y)) >> 1);
    }
  }

  /**
   * Calculate geometric average of x and y, i.e. sqrt (x * y) rounding down.
   * Revert on overflow or in case x * y is negative.
   *
   * @param x signed 64.64-bit fixed point number
   * @param y signed 64.64-bit fixed point number
   * @return signed 64.64-bit fixed point number
   */
  function gavg (int128 x, int128 y) internal pure returns (int128) {
    unchecked {
      int256 m = int256 (x) * int256 (y);
      require (m >= 0);
      require (m <
          0x4000000000000000000000000000000000000000000000000000000000000000);
      return int128 (sqrtu (uint256 (m)));
    }
  }

  /**
   * Calculate x^y assuming 0^0 is 1, where x is signed 64.64 fixed point number
   * and y is unsigned 256-bit integer number.  Revert on overflow.
   *
   * @param x signed 64.64-bit fixed point number
   * @param y uint256 value
   * @return signed 64.64-bit fixed point number
   */
  function pow (int128 x, uint256 y) internal pure returns (int128) {
    unchecked {
      bool negative = x < 0 && y & 1 == 1;

      uint256 absX = uint128 (x < 0 ? -x : x);
      uint256 absResult;
      absResult = 0x100000000000000000000000000000000;

      if (absX <= 0x10000000000000000) {
        absX <<= 63;
        while (y != 0) {
          if (y & 0x1 != 0) {
            absResult = absResult * absX >> 127;
          }
          absX = absX * absX >> 127;

          if (y & 0x2 != 0) {
            absResult = absResult * absX >> 127;
          }
          absX = absX * absX >> 127;

          if (y & 0x4 != 0) {
            absResult = absResult * absX >> 127;
          }
          absX = absX * absX >> 127;

          if (y & 0x8 != 0) {
            absResult = absResult * absX >> 127;
          }
          absX = absX * absX >> 127;

          y >>= 4;
        }

        absResult >>= 64;
      } else {
        uint256 absXShift = 63;
        if (absX < 0x1000000000000000000000000) { absX <<= 32; absXShift -= 32; }
        if (absX < 0x10000000000000000000000000000) { absX <<= 16; absXShift -= 16; }
        if (absX < 0x1000000000000000000000000000000) { absX <<= 8; absXShift -= 8; }
        if (absX < 0x10000000000000000000000000000000) { absX <<= 4; absXShift -= 4; }
        if (absX < 0x40000000000000000000000000000000) { absX <<= 2; absXShift -= 2; }
        if (absX < 0x80000000000000000000000000000000) { absX <<= 1; absXShift -= 1; }

        uint256 resultShift = 0;
        while (y != 0) {
          require (absXShift < 64);

          if (y & 0x1 != 0) {
            absResult = absResult * absX >> 127;
            resultShift += absXShift;
            if (absResult > 0x100000000000000000000000000000000) {
              absResult >>= 1;
              resultShift += 1;
            }
          }
          absX = absX * absX >> 127;
          absXShift <<= 1;
          if (absX >= 0x100000000000000000000000000000000) {
              absX >>= 1;
              absXShift += 1;
          }

          y >>= 1;
        }

        require (resultShift < 64);
        absResult >>= 64 - resultShift;
      }
      int256 result = negative ? -int256 (absResult) : int256 (absResult);
      require (result >= MIN_64x64 && result <= MAX_64x64);
      return int128 (result);
    }
  }

  /**
   * Calculate sqrt (x) rounding down.  Revert if x < 0.
   *
   * @param x signed 64.64-bit fixed point number
   * @return signed 64.64-bit fixed point number
   */
  function sqrt (int128 x) internal pure returns (int128) {
    unchecked {
      require (x >= 0);
      return int128 (sqrtu (uint256 (int256 (x)) << 64));
    }
  }

  /**
   * Calculate binary logarithm of x.  Revert if x <= 0.
   *
   * @param x signed 64.64-bit fixed point number
   * @return signed 64.64-bit fixed point number
   */
  function log_2 (int128 x) internal pure returns (int128) {
    unchecked {
      require (x > 0);

      int256 msb = 0;
      int256 xc = x;
      if (xc >= 0x10000000000000000) { xc >>= 64; msb += 64; }
      if (xc >= 0x100000000) { xc >>= 32; msb += 32; }
      if (xc >= 0x10000) { xc >>= 16; msb += 16; }
      if (xc >= 0x100) { xc >>= 8; msb += 8; }
      if (xc >= 0x10) { xc >>= 4; msb += 4; }
      if (xc >= 0x4) { xc >>= 2; msb += 2; }
      if (xc >= 0x2) msb += 1;  // No need to shift xc anymore

      int256 result = msb - 64 << 64;
      uint256 ux = uint256 (int256 (x)) << uint256 (127 - msb);
      for (int256 bit = 0x8000000000000000; bit > 0; bit >>= 1) {
        ux *= ux;
        uint256 b = ux >> 255;
        ux >>= 127 + b;
        result += bit * int256 (b);
      }

      return int128 (result);
    }
  }

  /**
   * Calculate natural logarithm of x.  Revert if x <= 0.
   *
   * @param x signed 64.64-bit fixed point number
   * @return signed 64.64-bit fixed point number
   */
  function ln (int128 x) internal pure returns (int128) {
    unchecked {
      require (x > 0);

      return int128 (int256 (
          uint256 (int256 (log_2 (x))) * 0xB17217F7D1CF79ABC9E3B39803F2F6AF >> 128));
    }
  }

  /**
   * Calculate binary exponent of x.  Revert on overflow.
   *
   * @param x signed 64.64-bit fixed point number
   * @return signed 64.64-bit fixed point number
   */
  function exp_2 (int128 x) internal pure returns (int128) {
    unchecked {
      require (x < 0x400000000000000000); // Overflow

      if (x < -0x400000000000000000) return 0; // Underflow

      uint256 result = 0x80000000000000000000000000000000;

      if (x & 0x8000000000000000 > 0)
        result = result * 0x16A09E667F3BCC908B2FB1366EA957D3E >> 128;
      if (x & 0x4000000000000000 > 0)
        result = result * 0x1306FE0A31B7152DE8D5A46305C85EDEC >> 128;
      if (x & 0x2000000000000000 > 0)
        result = result * 0x1172B83C7D517ADCDF7C8C50EB14A791F >> 128;
      if (x & 0x1000000000000000 > 0)
        result = result * 0x10B5586CF9890F6298B92B71842A98363 >> 128;
      if (x & 0x800000000000000 > 0)
        result = result * 0x1059B0D31585743AE7C548EB68CA417FD >> 128;
      if (x & 0x400000000000000 > 0)
        result = result * 0x102C9A3E778060EE6F7CACA4F7A29BDE8 >> 128;
      if (x & 0x200000000000000 > 0)
        result = result * 0x10163DA9FB33356D84A66AE336DCDFA3F >> 128;
      if (x & 0x100000000000000 > 0)
        result = result * 0x100B1AFA5ABCBED6129AB13EC11DC9543 >> 128;
      if (x & 0x80000000000000 > 0)
        result = result * 0x10058C86DA1C09EA1FF19D294CF2F679B >> 128;
      if (x & 0x40000000000000 > 0)
        result = result * 0x1002C605E2E8CEC506D21BFC89A23A00F >> 128;
      if (x & 0x20000000000000 > 0)
        result = result * 0x100162F3904051FA128BCA9C55C31E5DF >> 128;
      if (x & 0x10000000000000 > 0)
        result = result * 0x1000B175EFFDC76BA38E31671CA939725 >> 128;
      if (x & 0x8000000000000 > 0)
        result = result * 0x100058BA01FB9F96D6CACD4B180917C3D >> 128;
      if (x & 0x4000000000000 > 0)
        result = result * 0x10002C5CC37DA9491D0985C348C68E7B3 >> 128;
      if (x & 0x2000000000000 > 0)
        result = result * 0x1000162E525EE054754457D5995292026 >> 128;
      if (x & 0x1000000000000 > 0)
        result = result * 0x10000B17255775C040618BF4A4ADE83FC >> 128;
      if (x & 0x800000000000 > 0)
        result = result * 0x1000058B91B5BC9AE2EED81E9B7D4CFAB >> 128;
      if (x & 0x400000000000 > 0)
        result = result * 0x100002C5C89D5EC6CA4D7C8ACC017B7C9 >> 128;
      if (x & 0x200000000000 > 0)
        result = result * 0x10000162E43F4F831060E02D839A9D16D >> 128;
      if (x & 0x100000000000 > 0)
        result = result * 0x100000B1721BCFC99D9F890EA06911763 >> 128;
      if (x & 0x80000000000 > 0)
        result = result * 0x10000058B90CF1E6D97F9CA14DBCC1628 >> 128;
      if (x & 0x40000000000 > 0)
        result = result * 0x1000002C5C863B73F016468F6BAC5CA2B >> 128;
      if (x & 0x20000000000 > 0)
        result = result * 0x100000162E430E5A18F6119E3C02282A5 >> 128;
      if (x & 0x10000000000 > 0)
        result = result * 0x1000000B1721835514B86E6D96EFD1BFE >> 128;
      if (x & 0x8000000000 > 0)
        result = result * 0x100000058B90C0B48C6BE5DF846C5B2EF >> 128;
      if (x & 0x4000000000 > 0)
        result = result * 0x10000002C5C8601CC6B9E94213C72737A >> 128;
      if (x & 0x2000000000 > 0)
        result = result * 0x1000000162E42FFF037DF38AA2B219F06 >> 128;
      if (x & 0x1000000000 > 0)
        result = result * 0x10000000B17217FBA9C739AA5819F44F9 >> 128;
      if (x & 0x800000000 > 0)
        result = result * 0x1000000058B90BFCDEE5ACD3C1CEDC823 >> 128;
      if (x & 0x400000000 > 0)
        result = result * 0x100000002C5C85FE31F35A6A30DA1BE50 >> 128;
      if (x & 0x200000000 > 0)
        result = result * 0x10000000162E42FF0999CE3541B9FFFCF >> 128;
      if (x & 0x100000000 > 0)
        result = result * 0x100000000B17217F80F4EF5AADDA45554 >> 128;
      if (x & 0x80000000 > 0)
        result = result * 0x10000000058B90BFBF8479BD5A81B51AD >> 128;
      if (x & 0x40000000 > 0)
        result = result * 0x1000000002C5C85FDF84BD62AE30A74CC >> 128;
      if (x & 0x20000000 > 0)
        result = result * 0x100000000162E42FEFB2FED257559BDAA >> 128;
      if (x & 0x10000000 > 0)
        result = result * 0x1000000000B17217F7D5A7716BBA4A9AE >> 128;
      if (x & 0x8000000 > 0)
        result = result * 0x100000000058B90BFBE9DDBAC5E109CCE >> 128;
      if (x & 0x4000000 > 0)
        result = result * 0x10000000002C5C85FDF4B15DE6F17EB0D >> 128;
      if (x & 0x2000000 > 0)
        result = result * 0x1000000000162E42FEFA494F1478FDE05 >> 128;
      if (x & 0x1000000 > 0)
        result = result * 0x10000000000B17217F7D20CF927C8E94C >> 128;
      if (x & 0x800000 > 0)
        result = result * 0x1000000000058B90BFBE8F71CB4E4B33D >> 128;
      if (x & 0x400000 > 0)
        result = result * 0x100000000002C5C85FDF477B662B26945 >> 128;
      if (x & 0x200000 > 0)
        result = result * 0x10000000000162E42FEFA3AE53369388C >> 128;
      if (x & 0x100000 > 0)
        result = result * 0x100000000000B17217F7D1D351A389D40 >> 128;
      if (x & 0x80000 > 0)
        result = result * 0x10000000000058B90BFBE8E8B2D3D4EDE >> 128;
      if (x & 0x40000 > 0)
        result = result * 0x1000000000002C5C85FDF4741BEA6E77E >> 128;
      if (x & 0x20000 > 0)
        result = result * 0x100000000000162E42FEFA39FE95583C2 >> 128;
      if (x & 0x10000 > 0)
        result = result * 0x1000000000000B17217F7D1CFB72B45E1 >> 128;
      if (x & 0x8000 > 0)
        result = result * 0x100000000000058B90BFBE8E7CC35C3F0 >> 128;
      if (x & 0x4000 > 0)
        result = result * 0x10000000000002C5C85FDF473E242EA38 >> 128;
      if (x & 0x2000 > 0)
        result = result * 0x1000000000000162E42FEFA39F02B772C >> 128;
      if (x & 0x1000 > 0)
        result = result * 0x10000000000000B17217F7D1CF7D83C1A >> 128;
      if (x & 0x800 > 0)
        result = result * 0x1000000000000058B90BFBE8E7BDCBE2E >> 128;
      if (x & 0x400 > 0)
        result = result * 0x100000000000002C5C85FDF473DEA871F >> 128;
      if (x & 0x200 > 0)
        result = result * 0x10000000000000162E42FEFA39EF44D91 >> 128;
      if (x & 0x100 > 0)
        result = result * 0x100000000000000B17217F7D1CF79E949 >> 128;
      if (x & 0x80 > 0)
        result = result * 0x10000000000000058B90BFBE8E7BCE544 >> 128;
      if (x & 0x40 > 0)
        result = result * 0x1000000000000002C5C85FDF473DE6ECA >> 128;
      if (x & 0x20 > 0)
        result = result * 0x100000000000000162E42FEFA39EF366F >> 128;
      if (x & 0x10 > 0)
        result = result * 0x1000000000000000B17217F7D1CF79AFA >> 128;
      if (x & 0x8 > 0)
        result = result * 0x100000000000000058B90BFBE8E7BCD6D >> 128;
      if (x & 0x4 > 0)
        result = result * 0x10000000000000002C5C85FDF473DE6B2 >> 128;
      if (x & 0x2 > 0)
        result = result * 0x1000000000000000162E42FEFA39EF358 >> 128;
      if (x & 0x1 > 0)
        result = result * 0x10000000000000000B17217F7D1CF79AB >> 128;

      result >>= uint256 (int256 (63 - (x >> 64)));
      require (result <= uint256 (int256 (MAX_64x64)));

      return int128 (int256 (result));
    }
  }

  /**
   * Calculate natural exponent of x.  Revert on overflow.
   *
   * @param x signed 64.64-bit fixed point number
   * @return signed 64.64-bit fixed point number
   */
  function exp (int128 x) internal pure returns (int128) {
    unchecked {
      require (x < 0x400000000000000000); // Overflow

      if (x < -0x400000000000000000) return 0; // Underflow

      return exp_2 (
          int128 (int256 (x) * 0x171547652B82FE1777D0FFDA0D23A7D12 >> 128));
    }
  }

  /**
   * Calculate x / y rounding towards zero, where x and y are unsigned 256-bit
   * integer numbers.  Revert on overflow or when y is zero.
   *
   * @param x unsigned 256-bit integer number
   * @param y unsigned 256-bit integer number
   * @return unsigned 64.64-bit fixed point number
   */
  function divuu (uint256 x, uint256 y) private pure returns (uint128) {
    unchecked {
      require (y != 0);

      uint256 result;

      if (x <= 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF)
        result = (x << 64) / y;
      else {
        uint256 msb = 192;
        uint256 xc = x >> 192;
        if (xc >= 0x100000000) { xc >>= 32; msb += 32; }
        if (xc >= 0x10000) { xc >>= 16; msb += 16; }
        if (xc >= 0x100) { xc >>= 8; msb += 8; }
        if (xc >= 0x10) { xc >>= 4; msb += 4; }
        if (xc >= 0x4) { xc >>= 2; msb += 2; }
        if (xc >= 0x2) msb += 1;  // No need to shift xc anymore

        result = (x << 255 - msb) / ((y - 1 >> msb - 191) + 1);
        require (result <= 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF);

        uint256 hi = result * (y >> 128);
        uint256 lo = result * (y & 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF);

        uint256 xh = x >> 192;
        uint256 xl = x << 64;

        if (xl < lo) xh -= 1;
        xl -= lo; // We rely on overflow behavior here
        lo = hi << 128;
        if (xl < lo) xh -= 1;
        xl -= lo; // We rely on overflow behavior here

        result += xh == hi >> 128 ? xl / y : 1;
      }

      require (result <= 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF);
      return uint128 (result);
    }
  }

  /**
   * Calculate sqrt (x) rounding down, where x is unsigned 256-bit integer
   * number.
   *
   * @param x unsigned 256-bit integer number
   * @return unsigned 128-bit integer number
   */
  function sqrtu (uint256 x) private pure returns (uint128) {
    unchecked {
      if (x == 0) return 0;
      else {
        uint256 xx = x;
        uint256 r = 1;
        if (xx >= 0x100000000000000000000000000000000) { xx >>= 128; r <<= 64; }
        if (xx >= 0x10000000000000000) { xx >>= 64; r <<= 32; }
        if (xx >= 0x100000000) { xx >>= 32; r <<= 16; }
        if (xx >= 0x10000) { xx >>= 16; r <<= 8; }
        if (xx >= 0x100) { xx >>= 8; r <<= 4; }
        if (xx >= 0x10) { xx >>= 4; r <<= 2; }
        if (xx >= 0x4) { r <<= 1; }
        r = (r + x / r) >> 1;
        r = (r + x / r) >> 1;
        r = (r + x / r) >> 1;
        r = (r + x / r) >> 1;
        r = (r + x / r) >> 1;
        r = (r + x / r) >> 1;
        r = (r + x / r) >> 1; // Seven iterations should be enough
        uint256 r1 = x / r;
        return uint128 (r < r1 ? r : r1);
      }
    }
  }
}
// ---- end abdk-libraries-solidity/ABDKMath64x64.sol ----

// ---- begin @openzeppelin/contracts/security/ReentrancyGuard.sol ----
// OpenZeppelin Contracts (last updated v4.9.0) (security/ReentrancyGuard.sol)


/**
 * @dev Contract module that helps prevent reentrant calls to a function.
 *
 * Inheriting from `ReentrancyGuard` will make the {nonReentrant} modifier
 * available, which can be applied to functions to make sure there are no nested
 * (reentrant) calls to them.
 *
 * Note that because there is a single `nonReentrant` guard, functions marked as
 * `nonReentrant` may not call one another. This can be worked around by making
 * those functions `private`, and then adding `external` `nonReentrant` entry
 * points to them.
 *
 * TIP: If you would like to learn more about reentrancy and alternative ways
 * to protect against it, check out our blog post
 * https://blog.openzeppelin.com/reentrancy-after-istanbul/[Reentrancy After Istanbul].
 */
abstract contract ReentrancyGuard {
    // Booleans are more expensive than uint256 or any type that takes up a full
    // word because each write operation emits an extra SLOAD to first read the
    // slot's contents, replace the bits taken up by the boolean, and then write
    // back. This is the compiler's defense against contract upgrades and
    // pointer aliasing, and it cannot be disabled.

    // The values being non-zero value makes deployment a bit more expensive,
    // but in exchange the refund on every call to nonReentrant will be lower in
    // amount. Since refunds are capped to a percentage of the total
    // transaction's gas, it is best to keep them low in cases like this one, to
    // increase the likelihood of the full refund coming into effect.
    uint256 private constant _NOT_ENTERED = 1;
    uint256 private constant _ENTERED = 2;

    uint256 private _status;

    constructor() {
        _status = _NOT_ENTERED;
    }

    /**
     * @dev Prevents a contract from calling itself, directly or indirectly.
     * Calling a `nonReentrant` function from another `nonReentrant`
     * function is not supported. It is possible to prevent this from happening
     * by making the `nonReentrant` function external, and making it call a
     * `private` function that does the actual work.
     */
    modifier nonReentrant() {
        _nonReentrantBefore();
        _;
        _nonReentrantAfter();
    }

    function _nonReentrantBefore() private {
        // On the first call to nonReentrant, _status will be _NOT_ENTERED
        require(_status != _ENTERED, "ReentrancyGuard: reentrant call");

        // Any calls to nonReentrant after this point will fail
        _status = _ENTERED;
    }

    function _nonReentrantAfter() private {
        // By storing the original value once again, a refund is triggered (see
        // https://eips.ethereum.org/EIPS/eip-2200)
        _status = _NOT_ENTERED;
    }

    /**
     * @dev Returns true if the reentrancy guard is currently set to "entered", which indicates there is a
     * `nonReentrant` function in the call stack.
     */
    function _reentrancyGuardEntered() internal view returns (bool) {
        return _status == _ENTERED;
    }
}
// ---- end @openzeppelin/contracts/security/ReentrancyGuard.sol ----

// ---- begin BracketLMSR.sol ----
// Same fixed-point library as Labs 7 and 8 (signed 64.64 numbers).
// Same guard as the Lab 13 oracle (OpenZeppelin 4.9.6).

/// Read interface of the temperature oracle (see TemperatureOracle.sol).
interface ITemperatureOracle {
    /// @return exists     true if a report was stored for (station, day)
    /// @return tempF      daily maximum temperature, whole deg F
    /// @return reportedAt block timestamp of the report
    function getReport(string calldata station, uint32 day)
        external
        view
        returns (bool exists, int16 tempF, uint64 reportedAt);
}

/*
    Multi-outcome LMSR market on one station's daily maximum temperature.
    TESTNET ONLY. Class project (ECE 473). Not audited.

    Brackets
      `bounds` holds n-1 strictly increasing whole-degree boundaries.
        bracket 0     : T <  bounds[0]
        bracket j     : bounds[j-1] <= T < bounds[j]
        bracket n-1   : T >= bounds[n-2]
      The brackets are exhaustive and do not overlap. `strike` (90) must be
      one of the boundaries, so "T >= strike" is exactly the brackets
      strikeIndex .. n-1.

    Units
      Shares are whole numbers. One winning share pays `unit` wei.
      `b` is the LMSR liquidity parameter in shares (as in Lab 7).

    Cost function (log-sum-exp form, as in Lab 8, extended to n outcomes)
      C(q) = b * ln( sum_j exp(q_j / b) )
           = max(q) + b * ln( sum_j exp( (q_j - max(q)) / b ) )
      Every exponent is <= 0, so exp never overflows. The term of the
      largest q_j is exactly 1, so the sum is in [1, n] and ln is in [0, ln n].

    Charging rule
      costNow = C(q) is stored. A buy is charged C(q_new) - costNow.
      The charges telescope, so the total paid by traders is exactly
      C(q) - C(q0), whatever the order of the trades.

    Collateral rule
      The sponsor funds at least C(q0) at creation (q0 = 0 gives b*ln(n)).
      Then balance >= C(q) >= max(q) * unit >= any possible payout.
*/
contract BracketLMSR is ReentrancyGuard {
    using ABDKMath64x64 for int128;

    enum State { Open, Settled, Cancelled }

    // ---- input bounds (see docs/status/viktor.md) ----
    uint256 public constant MAX_BRACKETS = 32;
    uint256 public constant MAX_B = 1e12;        // shares
    uint256 public constant MAX_UNIT = 1 ether;  // wei per winning share
    uint256 public constant MAX_Q = 1e15;        // shares per bracket
    // exp(-x) is below 2^-64 for x >= 45 and is treated as 0.
    uint256 private constant EXP_CUTOFF = 45;
    int128 private constant ONE = 0x10000000000000000; // 1.0 in 64.64

    // ---- market definition ----
    address public immutable sponsor;
    ITemperatureOracle public immutable oracle;
    string public station;                 // e.g. "USW00014734"
    uint32 public immutable marketDay;     // UTC day number = unix time / 86400
    int16 public immutable strike;         // 90
    uint256 public immutable strikeIndex;  // first bracket with T >= strike
    uint256 public immutable b;            // liquidity parameter, in shares
    uint256 public immutable unit;         // wei paid per winning share
    uint64 public immutable tradingClose;    // buys allowed before this time
    uint64 public immutable observationEnd;  // a report must be made at or after this time
    uint64 public immutable reportDeadline;  // a report must be made at or before this time
    int16[] private bounds;

    // ---- market state ----
    State public state;
    uint256[] private q;        // LMSR quantities (seed q0 + shares sold)
    uint256[] private seed;     // q0, the sponsor's prior. Pays nobody.
    uint256 public costNow;     // C(q) in wei
    uint256 public requiredFunding; // C(q0) in wei
    uint256 public funding;     // wei sent by the sponsor at creation
    uint256 public totalPaid;   // wei paid by all traders
    uint256 public reserved;    // wei still owed to traders after settle/cancel
    int16 public settledTemp;
    uint256 public winningBracket;

    mapping(address => mapping(uint256 => uint256)) public sharesOf; // trader => bracket => shares
    mapping(address => uint256) public paid;                          // trader => wei paid (cost basis)

    // ---- events (one per state change) ----
    event MarketCreated(address indexed sponsor, address indexed oracle, string station, uint32 marketDay,
        uint256 numBrackets, int16 strike, uint256 b, uint256 unit, uint256 funding, uint256 requiredFunding);
    event Trade(address indexed trader, uint256 indexed bracket, uint256 shares, uint256 cost);
    event BasketTrade(address indexed trader, uint256 firstBracket, uint256 lastBracket, uint256 sharesEach, uint256 cost);
    event Settled(int16 tempF, uint256 indexed winningBracket, uint64 reportedAt, uint256 owedToWinners);
    event Cancelled(address indexed caller, string reason, uint256 owedToTraders);
    event Redeemed(address indexed trader, uint256 shares, uint256 amount);
    event Refunded(address indexed trader, uint256 amount);
    event SponsorWithdrawal(address indexed sponsor, uint256 amount);

    modifier onlySponsor() {
        require(msg.sender == sponsor, "Not sponsor");
        _;
    }

    /// @param _oracle         TemperatureOracle (or MockOracle in tests)
    /// @param _station        station id the oracle reports under
    /// @param _marketDay      UTC day number (unix time / 86400) of the settled day
    /// @param _bounds         n-1 increasing bracket boundaries in deg F
    /// @param _strike         boundary used by the basket ("T >= strike"), 90
    /// @param _b              LMSR liquidity parameter, in shares
    /// @param _unit           wei paid per winning share
    /// @param _initialQ       empty for a uniform prior, or n seed quantities with minimum 0
    /// @param _tradingClose   unix time, end of trading
    /// @param _observationEnd unix time, end of the observed day (>= _tradingClose)
    /// @param _reportDeadline unix time, last moment for a valid report
    /// msg.value must cover the worst-case loss C(q0) (= b*ln(n)*unit for a uniform prior).
    constructor(
        address _oracle,
        string memory _station,
        uint32 _marketDay,
        int16[] memory _bounds,
        int16 _strike,
        uint256 _b,
        uint256 _unit,
        uint256[] memory _initialQ,
        uint64 _tradingClose,
        uint64 _observationEnd,
        uint64 _reportDeadline
    ) payable {
        require(_oracle != address(0), "Zero oracle");
        require(_b > 0 && _b <= MAX_B, "b out of range");
        require(_unit > 0 && _unit <= MAX_UNIT, "unit out of range");
        require(_tradingClose > block.timestamp, "Trading close in the past");
        require(_observationEnd >= _tradingClose, "Observation ends before trading");
        require(_reportDeadline > _observationEnd, "Deadline before observation end");

        sponsor = msg.sender;
        oracle = ITemperatureOracle(_oracle);
        station = _station;
        marketDay = _marketDay;
        strike = _strike;
        b = _b;
        unit = _unit;
        tradingClose = _tradingClose;
        observationEnd = _observationEnd;
        reportDeadline = _reportDeadline;

        strikeIndex = _checkBounds(_bounds, _strike);
        bounds = _bounds;

        uint256 n = _bounds.length + 1;
        uint256[] memory q0 = new uint256[](n);
        if (_initialQ.length != 0) {
            require(_initialQ.length == n, "initialQ length");
            uint256 lowest = type(uint256).max;
            for (uint256 j = 0; j < n; j++) {
                require(_initialQ[j] <= MAX_Q, "initialQ too large");
                if (_initialQ[j] < lowest) lowest = _initialQ[j];
                q0[j] = _initialQ[j];
            }
            require(lowest == 0, "initialQ minimum must be 0");
        }
        q = q0;
        seed = q0;

        uint256 c0 = _cost(q0, _b, _unit);
        require(msg.value >= c0, "Funding below worst-case loss");
        costNow = c0;
        requiredFunding = c0;
        funding = msg.value;

        emit MarketCreated(msg.sender, _oracle, _station, _marketDay, n, _strike, _b, _unit, msg.value, c0);
    }

    // ------------------------------------------------------------------
    // Views
    // ------------------------------------------------------------------

    function numBrackets() public view returns (uint256) {
        return q.length;
    }

    function getBounds() external view returns (int16[] memory) {
        return bounds;
    }

    /// LMSR quantities per bracket (seed + sold).
    function getQuantities() external view returns (uint256[] memory) {
        return q;
    }

    /// Shares sold to traders per bracket (these are the only shares that pay).
    function getSold() public view returns (uint256[] memory sold) {
        uint256 n = q.length;
        sold = new uint256[](n);
        for (uint256 j = 0; j < n; j++) sold[j] = q[j] - seed[j];
    }

    /// Bracket index that contains temperature `tempF`.
    function bracketOf(int16 tempF) public view returns (uint256) {
        uint256 m = bounds.length;
        for (uint256 j = 0; j < m; j++) {
            if (tempF < bounds[j]) return j;
        }
        return m;
    }

    /// LMSR cost C(q) in wei for an arbitrary quantity vector (testing aid).
    function costOf(uint256[] memory quantities) external view returns (uint256) {
        require(quantities.length == q.length, "Length");
        return _cost(quantities, b, unit);
    }

    /// Instantaneous prices of all brackets, 1e18 = 100%. They sum to 1 up to rounding down.
    function prices() public view returns (uint256[] memory p) {
        uint256 n = q.length;
        uint256[] memory qm = q;
        (int128[] memory e, int128 sum) = _weights(qm, b);
        p = new uint256[](n);
        for (uint256 j = 0; j < n; j++) p[j] = e[j].div(sum).mulu(1e18);
    }

    /// Instantaneous price of one bracket, 1e18 = 100%.
    function price(uint256 bracket) external view returns (uint256) {
        require(bracket < q.length, "Bad bracket");
        return prices()[bracket];
    }

    /// Instantaneous price of "T >= strike" (sum of the basket brackets), 1e18 = 100%.
    function priceAtOrAboveStrike() external view returns (uint256 total) {
        uint256[] memory p = prices();
        for (uint256 j = strikeIndex; j < p.length; j++) total += p[j];
    }

    /// Wei needed to buy `shares` of one bracket now.
    function quoteBuy(uint256 bracket, uint256 shares) public view returns (uint256) {
        require(bracket < q.length, "Bad bracket");
        (uint256 cost, ) = _quote(bracket, bracket, shares);
        return cost;
    }

    /// Wei needed to buy `sharesEach` of every bracket at or above the strike now.
    /// The basket pays sharesEach * unit if T >= strike, else 0.
    function quoteBasket(uint256 sharesEach) public view returns (uint256) {
        (uint256 cost, ) = _quote(strikeIndex, q.length - 1, sharesEach);
        return cost;
    }

    /// Largest amount the contract could owe to traders right now, in wei.
    function maxLiability() public view returns (uint256) {
        if (state != State.Open) return reserved;
        uint256 n = q.length;
        uint256 top = 0;
        for (uint256 j = 0; j < n; j++) {
            uint256 s = q[j] - seed[j];
            if (s > top) top = s;
        }
        uint256 payout = top * unit;
        // On a cancel the traders get their cost basis back instead.
        return payout > totalPaid ? payout : totalPaid;
    }

    // ------------------------------------------------------------------
    // Trading
    // ------------------------------------------------------------------

    /// Buy whole shares of one bracket. Reverts if the cost exceeds `maxCost`.
    /// Send at least the cost; the excess is returned.
    function buy(uint256 bracket, uint256 shares, uint256 maxCost) external payable nonReentrant {
        require(bracket < q.length, "Bad bracket");
        uint256 cost = _buyRange(bracket, bracket, shares, maxCost);
        emit Trade(msg.sender, bracket, shares, cost);
        _refundExcess(cost);
    }

    /// Buy `sharesEach` of every bracket at or above the strike in one transaction.
    /// All legs fill or none. Reverts if the total cost exceeds `maxCost`.
    function buyBasket(uint256 sharesEach, uint256 maxCost) external payable nonReentrant {
        uint256 last = q.length - 1;
        uint256 cost = _buyRange(strikeIndex, last, sharesEach, maxCost);
        emit BasketTrade(msg.sender, strikeIndex, last, sharesEach, cost);
        _refundExcess(cost);
    }

    // ------------------------------------------------------------------
    // Settlement and cancellation
    // ------------------------------------------------------------------

    /// Settle with the oracle's report for the market day. Anyone may call.
    /// The report must exist, be made at or after observationEnd (not stale)
    /// and at or before reportDeadline (not late). Works once.
    function settle() external nonReentrant {
        require(state == State.Open, "Not open");
        require(block.timestamp >= observationEnd, "Observation not over");
        (bool exists, int16 tempF, uint64 reportedAt) = oracle.getReport(station, marketDay);
        require(exists, "No report for market day");
        require(reportedAt >= observationEnd, "Stale report");
        require(reportedAt <= reportDeadline, "Late report");

        uint256 w = bracketOf(tempF);
        state = State.Settled;
        settledTemp = tempF;
        winningBracket = w;
        reserved = (q[w] - seed[w]) * unit;
        emit Settled(tempF, w, reportedAt, reserved);
    }

    /// After the deadline, anyone may cancel if there is no valid report.
    /// A missing, stale, late or unreadable report all end here.
    function cancelAfterDeadline() external nonReentrant {
        require(state == State.Open, "Not open");
        require(block.timestamp > reportDeadline, "Deadline not passed");
        require(!_hasValidReport(), "Valid report exists, call settle");
        _cancel("No valid report by deadline");
    }

    /// Emergency stop: the sponsor may cancel while trading is still open.
    /// Not allowed after tradingClose, so the sponsor cannot cancel a market
    /// once the temperature is being observed and a loss is in sight.
    /// After tradingClose the only exits are settle() and cancelAfterDeadline().
    function emergencyCancel() external onlySponsor nonReentrant {
        require(state == State.Open, "Not open");
        require(block.timestamp < tradingClose, "Trading closed, wait for the oracle");
        _cancel("Emergency cancel by sponsor");
    }

    // ------------------------------------------------------------------
    // Payouts
    // ------------------------------------------------------------------

    /// After settlement: winning shares pay `unit` wei each.
    function redeem() external nonReentrant {
        require(state == State.Settled, "Not settled");
        uint256 shares = sharesOf[msg.sender][winningBracket];
        require(shares > 0, "Nothing to redeem");
        uint256 amount = shares * unit;
        sharesOf[msg.sender][winningBracket] = 0;
        reserved -= amount;
        emit Redeemed(msg.sender, shares, amount);
        _send(msg.sender, amount);
    }

    /// After a cancel: each trader gets back exactly what they paid (cost basis).
    function claimRefund() external nonReentrant {
        require(state == State.Cancelled, "Not cancelled");
        uint256 amount = paid[msg.sender];
        require(amount > 0, "Nothing to refund");
        paid[msg.sender] = 0;
        reserved -= amount;
        emit Refunded(msg.sender, amount);
        _send(msg.sender, amount);
    }

    /// After settlement or cancel: the sponsor takes everything not owed to traders.
    function sponsorWithdraw() external onlySponsor nonReentrant {
        require(state != State.Open, "Market still open");
        uint256 amount = address(this).balance - reserved;
        require(amount > 0, "Nothing to withdraw");
        emit SponsorWithdrawal(msg.sender, amount);
        _send(msg.sender, amount);
    }

    // ------------------------------------------------------------------
    // Internals
    // ------------------------------------------------------------------

    function _checkBounds(int16[] memory _bounds, int16 _strike) private pure returns (uint256 idx) {
        uint256 m = _bounds.length;
        require(m >= 1 && m + 1 <= MAX_BRACKETS, "Bad number of brackets");
        bool found = false;
        for (uint256 j = 0; j < m; j++) {
            if (j > 0) require(_bounds[j] > _bounds[j - 1], "Bounds not increasing");
            if (_bounds[j] == _strike) {
                found = true;
                idx = j + 1; // bracket j+1 starts at bounds[j]
            }
        }
        require(found, "Strike is not a boundary");
    }

    /// exp((q_j - max q) / b) for every j, and their sum, as 64.64 numbers.
    function _weights(uint256[] memory qm, uint256 _b) private pure returns (int128[] memory e, int128 sum) {
        uint256 n = qm.length;
        uint256 top = 0;
        uint256 iTop = 0;
        for (uint256 j = 0; j < n; j++) {
            if (qm[j] > top) {
                top = qm[j];
                iTop = j;
            }
        }
        e = new int128[](n);
        for (uint256 j = 0; j < n; j++) {
            if (j == iTop) {
                e[j] = ONE; // exp(0), exact
            } else {
                uint256 d = top - qm[j];
                // Below 2^-64 the weight is 0. The check also keeps divu in range.
                if (d < EXP_CUTOFF * _b) e[j] = ABDKMath64x64.divu(d, _b).neg().exp();
            }
            sum = sum.add(e[j]);
        }
    }

    /// C(q) in wei = max(q)*unit + floor( ln(sum) * b * unit ).
    function _cost(uint256[] memory qm, uint256 _b, uint256 _unit) private pure returns (uint256) {
        uint256 n = qm.length;
        uint256 top = 0;
        for (uint256 j = 0; j < n; j++) if (qm[j] > top) top = qm[j];
        (, int128 sum) = _weights(qm, _b);
        return top * _unit + sum.ln().mulu(_b * _unit);
    }

    /// Cost of adding `shares` to every bracket in [first, last], and the new C(q).
    function _quote(uint256 first, uint256 last, uint256 shares) private view returns (uint256 cost, uint256 newCost) {
        require(shares > 0, "Zero shares");
        uint256[] memory qm = q;
        for (uint256 j = first; j <= last; j++) {
            qm[j] += shares;
            require(qm[j] <= MAX_Q, "Quantity too large");
        }
        newCost = _cost(qm, b, unit);
        // C is increasing in q. The guard only matters for rounding at the last wei.
        cost = newCost > costNow ? newCost - costNow : 0;
    }

    function _buyRange(uint256 first, uint256 last, uint256 shares, uint256 maxCost) private returns (uint256 cost) {
        require(state == State.Open, "Not open");
        require(block.timestamp < tradingClose, "Trading closed");
        uint256 newCost;
        (cost, newCost) = _quote(first, last, shares);
        require(cost <= maxCost, "Cost above slippage limit");
        require(msg.value >= cost, "Insufficient payment");

        // effects
        for (uint256 j = first; j <= last; j++) {
            q[j] += shares;
            sharesOf[msg.sender][j] += shares;
        }
        if (newCost > costNow) costNow = newCost;
        paid[msg.sender] += cost;
        totalPaid += cost;
    }

    function _hasValidReport() private view returns (bool) {
        try oracle.getReport(station, marketDay) returns (bool exists, int16, uint64 reportedAt) {
            return exists && reportedAt >= observationEnd && reportedAt <= reportDeadline;
        } catch {
            return false; // a broken oracle must not block refunds
        }
    }

    function _cancel(string memory reason) private {
        state = State.Cancelled;
        reserved = totalPaid;
        emit Cancelled(msg.sender, reason, totalPaid);
    }

    function _refundExcess(uint256 cost) private {
        if (msg.value > cost) _send(msg.sender, msg.value - cost);
    }

    function _send(address to, uint256 amount) private {
        (bool ok, ) = payable(to).call{value: amount}("");
        require(ok, "Transfer failed");
    }
}
// ---- end BracketLMSR.sol ----
