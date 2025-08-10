from setuptools import setup

# Get the version without importing the entire module.
# This avoids the premature import of 'requests'.
version = '2.3.2'
with open("smtp2go/core.py") as f:
    for line in f:
        if line.startswith('__version__'):
            version = eval(line.split('=')[-1])
            break

setup(name='smtp2go',
      version=version,
      description='Library for interfacing with the smtp2go API.',
      url='https://github.com/smtp2go-oss/smtp2go-python',
      author='smtp2go',
      author_email='support@quatrixglobal.com',
      license='MIT',
      packages=['smtp2go'],
      install_requires=[
          'requests'
      ],
      classifiers=[
          "Development Status :: 5 - Production/Stable",
          "Intended Audience :: Developers",
          "License :: OSI Approved :: MIT License",
          "Programming Language :: Python :: 2.7",
          "Programming Language :: Python :: 3",
          "Topic :: Communications :: Email",
          "Topic :: Software Development :: Libraries :: Python Modules",
      ],
      zip_safe=False)
