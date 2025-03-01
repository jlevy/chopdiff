import tiktoken


def tiktoken_len(string: str, encoding_name: str = "o200k_base") -> int:
    """
    Length of text in tiktokens.
    """
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens
