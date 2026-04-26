from setuptools import setup, find_packages

setup(
    name="pro-hunter",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "playwright",
        "httpx",
        "pyyaml",
        "browser-use",
        "langchain-ollama",
        "langchain-openai",
        "langchain-community",
        "beautifulsoup4",
        "pandas",
        "chromadb",
        "pdfplumber",
        "openai",
        "requests",
    ],
    python_requires=">=3.10",
)
