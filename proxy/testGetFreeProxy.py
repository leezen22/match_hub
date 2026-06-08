# -*- coding: utf-8 -*-
"""
-------------------------------------------------
   File Name：     testGetFreeProxy
   Description :   test model ProxyGetter/getFreeProxy
   Author :        J_hao
   date：          2017/7/31
-------------------------------------------------
   Change Activity:
                   2017/7/31:function testGetFreeProxy
-------------------------------------------------
"""
from proxy.getFreeProxy import GetFreeProxy

__author__ = 'J_hao'


def testGetFreeProxy():
    """
    test class GetFreeProxy in ProxyGetter/GetFreeProxy
    :return:
    """
    proxys=[]
    proxy_getter_functions = [
        # "freeProxy01",
        "freeProxy02",
        "freeProxy03",
        "freeProxy04",
        "freeProxy05",
        "freeProxy06",
        "freeProxy07",
        # "freeProxy08",
        "freeProxy09",
    ]
    for proxyGetter in proxy_getter_functions:
        # proxy_count = 0
        for proxy in getattr(GetFreeProxy, proxyGetter.strip())():
            if proxy:
                proxys.append(proxy)
                # print('{func}: fetch proxy {proxy},proxy_count:{proxy_count}'.format(func=proxyGetter, proxy=proxy,
                #                                                                      proxy_count=proxy_count))
                # proxy_count += 1
        # assert proxy_count >= 20, '{} fetch proxy fail'.format(proxyGetter)
    return proxys

# if __name__ == '__main__':
#     proxys = testGetFreeProxy()
#     print(proxys)
