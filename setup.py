import os
import setuptools

setuptools.setup(
    name="tgmb",
    version="0.0.0" + 'b' + os.environ["PKG_VER"].replace('refs/tags/v', '').replace('.', '').replace('b', ''),
    author="SomesH S",
    author_email="ksssomesh12@gmail.com",
    description="Predecessor to `tgmb`",
    long_description=open('README.md', 'rt', encoding='utf-8').read(),
    long_description_content_type="text/markdown",
    url="https://github.com/ksssomesh12/tgmb-beta",
    project_urls={
        "Bug Tracker": "https://github.com/ksssomesh12/tgmb-beta/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Development Status :: 4 - Beta"
    ],
    packages=setuptools.find_packages(),
    install_requires=open('requirements.txt', 'rt', encoding='utf-8').read().split('\n'),
    python_requires=">=3.8"
)
