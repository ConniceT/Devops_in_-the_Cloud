from setuptools import setup, find_packages

setup(
    name="trading_bot",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pandas>=1.5.0",
        "numpy>=1.21.0",
        "requests>=2.26.0",
        "zoneinfo>=2.1.0"
    ],
    entry_points={
        'console_scripts': [
            'trading-bot=src.run:main',
        ],
    },
)
