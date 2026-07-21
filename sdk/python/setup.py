from setuptools import find_packages, setup

setup(
    name="aegis-sdk",
    version="0.1.0",
    description="Governance and permission SDK for AI agents",
    author="Jose",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "requests>=2.31.0",
    ],
    extras_require={
        "dev": [
            "pytest>=8.0.0",
            "pytest-mock>=3.12.0",
            "responses>=0.25.0",
        ],
    },
)
