import re,requests,random


def get_ip_list(url,headers):
    htmls = requests.get(url,headers=headers).text
    root_pattern = 'alt="Cn" /></td>([\d\D]*?)</tr>'
    root = re.findall(root_pattern,htmls)
    list_ip = []
    # 再次匹配数据，把数据存入列表
    for i in range(len(root)):
        key = re.findall('<td>([\d\D]*?)</td>', root[i])
        list_ip.append(key[3].lower()+'://'+key[0]+':'+key[1])
    return list_ip


def get_random_ip(list_ip):
    list_proxy = list_ip
    proxy= random.choice(list_proxy)
    if 'https' in proxy:
        return {'https': proxy}
    else:
        return {'http': proxy}


def get_proxy():
    url = "https://www.xicidaili.com/wt/"
    user_agent_list = [
        "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; WOW64) Gecko/20100101 Firefox/61.0",
        "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.62 Safari/537.36",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.101 Safari/537.36",
        "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0)",
        "Mozilla/5.0 (Macintosh; U; PPC Mac OS X 10.5; en-US; rv:1.9.2.15) Gecko/20110303 Firefox/3.6.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36"
    ]
    headers = {'User-Agent': random.choice(user_agent_list)}
    list_ip = get_ip_list(url,headers)
    proxy = get_random_ip(list_ip)
    return proxy