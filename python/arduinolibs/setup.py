from distutils.core import setup, Extension
import sys
from os import path

path_libs = '../../tmp/arduinolibs/libraries'


def main():

    if sys.version_info >= (3,):
        BOOST_LIB = 'boost_python3'
    else:
        BOOST_LIB = 'boost_python'

    setup(name="arduinolibslw",
          version="0.1.0",
          description=
          """
          Python interface for the light-weight (LW) 
          rweather arduinolibs C library (https://github.com/rweather/arduinolibs)
          """,
          author="Mathieu Dugre",
          author_email="mathieu.dugre@mdugre.info",
          ext_modules=[Extension(
              "arduinolibslw",
              [
                  path.join(path_libs, "Crypto/Crypto.cpp"),
                  path.join(path_libs, "Crypto/Cipher.cpp"),
                  path.join(path_libs, "Crypto/AuthenticatedCipher.cpp"),
                  path.join(path_libs, "CryptoLW/src/Acorn128.cpp"),
                  path.join(path_libs, "CryptoLW/src/Ascon128.cpp"),
                  "arduinolibs.cpp",
              ],
              libraries=[BOOST_LIB],
              include_dirs=[
                  path.join(path_libs, "Crypto"),
                  path.join(path_libs, "Crypto/utility"),
                  path.join(path_libs, "CryptoLW/src"),
              ]
          )])


if __name__ == "__main__":
    main()
