import json
from datetime import datetime
from Crypto.Cipher import AES
import base64
import requests

# 配置参数
LIST_API_URL = "https://tro.ipsebe.com/api/TroSearch/queryTroSearchList"
DETAIL_API_URL = "https://tro.ipsebe.com/api/TroSearch/getBrand"
KEY = "1234567890abddef"  # 16字节AES密钥
IV = "absebe1234567890"  # 16字节初始向量

# 请求头配置
headers = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'Connection': 'keep-alive',
    'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
    'Origin': 'https://tro.ipsebe.com',
    'Referer': 'https://tro.ipsebe.com/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0',
    'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Microsoft Edge";v="138"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}


def pkcs7_unpad(data):
    """去除PKCS7填充"""
    if not data:
        return data
    pad_length = data[-1]
    if pad_length < 1 or pad_length > len(data):
        raise ValueError("无效的PKCS7填充")
    return data[:-pad_length]


def aes_cbc_decrypt(encrypted_data):
    """AES-CBC解密函数"""
    try:
        key_bytes = KEY.encode('utf-8')
        iv_bytes = IV.encode('utf-8')
        if len(key_bytes) != 16 or len(iv_bytes) != 16:
            raise ValueError("密钥和初始向量必须为16字节长度")

        cipher_text = base64.b64decode(encrypted_data)
        cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
        decrypted_bytes = cipher.decrypt(cipher_text)
        plaintext = pkcs7_unpad(decrypted_bytes).decode('utf-8')
        return {"success": True, "data": plaintext}
    except Exception as e:
        return {"success": False, "error": f"解密失败: {str(e)}"}


def timestamp_to_datetime(timestamp):
    """将毫秒级时间戳转换为标准日期格式（YYYY-MM-DD）"""
    try:
        if isinstance(timestamp, (int, float)):
            # 处理毫秒级时间戳（转换为秒）
            if len(str(int(timestamp))) > 10:
                timestamp = timestamp / 1000
            return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
        return "非时间戳格式"
    except Exception as e:
        return f"转换失败: {str(e)}"


def extract_brand_info(decrypted_json):
    """提取列表数据中的品牌基本信息"""
    try:
        data = json.loads(decrypted_json)
        if "list" not in data:
            return {"success": False, "error": "数据中不包含list字段"}

        result = []
        for item in data["list"]:
            column_values = item.get("columnValues", [])
            total_values = len(column_values)

            first_value = column_values[0] if total_values > 0 else None
            second_value = column_values[1] if total_values > 1 else None
            third_value = column_values[2] if total_values > 2 else None
            seventh_value = column_values[6] if total_values > 6 else None
            last_value = column_values[-1] if total_values > 0 else None

            # 转换时间戳为日期
            formatted_date = timestamp_to_datetime(first_value)

            info = {
                "id": item["columns"].get("id"),
                "caseNo": item["columns"].get("caseNo"),
                "brand_name": item["columns"].get("brand_name"),
                "brand_id": item["columns"].get("brand_id"),  # 保留用于获取详情，但不显示
                "filing_timestamp": first_value,
                "filing_date": formatted_date,
                "plaintiff": second_value,  # 原告
                "law_firm": third_value,  # 原告律所
                "case_type": seventh_value,  # 起诉类型
                "last_value_brand_id": last_value
            }
            result.append(info)

        return {"success": True, "data": result, "total": len(result)}
    except json.JSONDecodeError:
        return {"success": False, "error": "解密结果不是有效的JSON格式"}
    except Exception as e:
        return {"success": False, "error": f"数据提取失败: {str(e)}"}


def extract_specific_details(detail_data):
    """提取详细信息中的plaintiffIntroduction、brandCode和所有URL链接"""
    extracted = {
        "plaintiff_introduction": None,
        "brand_code": None,  # 版权号码
        "urls": []
    }

    # 提取原告介绍
    if "caseBrand" in detail_data and "plaintiffIntroduction" in detail_data["caseBrand"]:
        extracted["plaintiff_introduction"] = detail_data["caseBrand"]["plaintiffIntroduction"]

    # 提取brandCode作为版权号码
    if "caseBrand" in detail_data and "brandCode" in detail_data["caseBrand"]:
        extracted["brand_code"] = detail_data["caseBrand"]["brandCode"]

    # 提取品牌头像图片URL
    if "caseBrand" in detail_data and "brandHeadPicList" in detail_data["caseBrand"]:
        for item in detail_data["caseBrand"]["brandHeadPicList"]:
            if "url" in item:
                extracted["urls"].append({
                    "type": "品牌头像",
                    "name": item.get("name", "未命名图片"),
                    "url": item["url"]
                })

    # 提取维权材料URL
    if "caseBrand" in detail_data and "rightsProtectionList" in detail_data["caseBrand"]:
        for item in detail_data["caseBrand"]["rightsProtectionList"]:
            if "url" in item:
                extracted["urls"].append({
                    "type": "维权材料",
                    "name": item.get("name", "未命名文件"),
                    "url": item["url"]
                })

    return extracted


def fetch_brand_details(brand_id):
    """根据brand_id获取品牌详细信息并解密"""
    try:
        data = {'brandId': str(brand_id)}
        response = requests.post(
            DETAIL_API_URL,
            headers=headers,
            data=data,
            timeout=10
        )
        response.raise_for_status()
        api_result = response.json()

        if api_result.get("code") != 0:
            return {"success": False, "error": f"详情API错误: {api_result.get('msg', '未知错误')}"}

        encrypted_content = api_result.get("data")
        if not encrypted_content:
            return {"success": False, "error": "详情API返回加密数据为空"}

        # 解密详细信息
        decrypt_result = aes_cbc_decrypt(encrypted_content)
        if not decrypt_result["success"]:
            return decrypt_result

        # 解析并提取特定字段
        try:
            details = json.loads(decrypt_result["data"])
            specific_details = extract_specific_details(details)
            return {
                "success": True,
                "data": details,
                "specific": specific_details
            }
        except json.JSONDecodeError:
            return {"success": False, "error": "品牌详情解密结果不是有效的JSON格式"}

    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"详情请求失败: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"详情处理失败: {str(e)}"}


def fetch_and_decrypt(page=1, limit=20, fetch_details=True):
    """完整流程：请求列表→解密→提取数据→获取详细信息"""
    try:
        request_data = {'page': str(page), 'limit': str(limit)}
        response = requests.post(
            LIST_API_URL,
            headers=headers,
            data=request_data,
            timeout=10
        )
        response.raise_for_status()
        api_result = response.json()

        if api_result.get("code") != 0:
            return {"success": False, "error": f"列表API错误: {api_result.get('msg', '未知错误')}"}

        encrypted_content = api_result.get("data")
        if not encrypted_content:
            return {"success": False, "error": "列表API返回加密数据为空"}

        # 解密列表数据
        decrypt_result = aes_cbc_decrypt(encrypted_content)
        if not decrypt_result["success"]:
            return decrypt_result

        # 提取列表信息
        extract_result = extract_brand_info(decrypt_result["data"])
        if not extract_result["success"]:
            return extract_result

        # 获取详细信息
        if fetch_details:
            for item in extract_result["data"]:
                # 仍然使用brand_id获取详情，但不在最终显示
                brand_id = item.get("brand_id") or item.get("last_value_brand_id")
                if brand_id:
                    details_result = fetch_brand_details(brand_id)
                    item["details"] = details_result if details_result["success"] else None
                else:
                    item["details"] = None

        return extract_result

    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"列表请求失败: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"列表处理失败: {str(e)}"}


def save_to_json(data, filename="brand_info.json"):
    """将结果保存为JSON文件"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n数据已成功保存到 {filename}")
    except Exception as e:
        print(f"\n保存文件失败: {str(e)}")


if __name__ == "__main__":
    # 配置参数
    START_PAGE = 1  # 起始页码
    LIMIT = 20  # 每页条数
    FETCH_DETAILS = True  # 是否获取详情
    SAVE_TO_FILE = True  # 是否保存结果到文件
    MAX_RETRY = 3  # 单页最大重试次数
    DELAY_BETWEEN_PAGES = 0.5  # 页面间请求延迟(秒)，避免请求过于频繁

    # 存储所有页面的数据
    all_results = []
    current_page = START_PAGE
    has_more_data = True

    while has_more_data:
        retry_count = 0
        success = False

        # 页面请求重试机制
        while retry_count < MAX_RETRY and not success:
            print(f"\n----- 开始获取第 {current_page} 页数据 -----")
            result = fetch_and_decrypt(page=current_page, limit=LIMIT, fetch_details=FETCH_DETAILS)

            if result["success"]:
                # 检查是否有数据
                if result["total"] > 0:
                    print(f"✅ 第 {current_page} 页成功提取 {result['total']} 条数据")
                    all_results.extend(result["data"])

                    # 打印当前页数据摘要
                    for i, item in enumerate(result["data"], 1):
                        print(f"\n===== 第 {current_page} 页 条目 {i} =====")
                        print(f"案件号: {item['caseNo']}")
                        print(f"原告律所: {item['law_firm']}")
                        print(f"原告: {item['plaintiff']}")
                        print(f"涉案知识产权: {item['brand_name']}")
                        print(f"起诉类型: {item['case_type']}")
                        print(f"起诉日: {item['filing_date']}")

                        if item["details"] and item["details"]["success"]:
                            specific = item["details"]["specific"]
                            print(f"版权号码: {specific['brand_code'] or '未找到'}")

                            print("\n----- 权利人简介 -----")
                            if specific["plaintiff_introduction"]:
                                print(specific["plaintiff_introduction"])
                            else:
                                print("未找到权利人简介")

                            print("\n----- 相关链接 -----")
                            if specific["urls"]:
                                for idx, url_info in enumerate(specific["urls"], 1):
                                    print(f"{idx}. {url_info['type']}: {url_info['name']}")
                                    print(f"   {url_info['url']}")
                            else:
                                print("未找到相关链接")
                        else:
                            error_msg = item["details"]["error"] if (
                                        item["details"] and "error" in item["details"]) else "无详细信息"
                            print(f"详细信息: 获取失败 - {error_msg}")

                    success = True
                    current_page += 1

                    # 页面间添加延迟，避免请求过于频繁
                    if DELAY_BETWEEN_PAGES > 0:
                        import time

                        print(f"\n等待 {DELAY_BETWEEN_PAGES} 秒后获取下一页数据...")
                        time.sleep(DELAY_BETWEEN_PAGES)
                else:
                    # 无数据，结束翻页
                    print(f"ℹ️ 第 {current_page} 页未返回数据，已到达最后一页")
                    has_more_data = False
                    success = True
            else:
                retry_count += 1
                print(f"❌ 第 {current_page} 页获取失败（{retry_count}/{MAX_RETRY}）: {result['error']}")
                if retry_count < MAX_RETRY:
                    # 重试前等待1秒
                    import time

                    time.sleep(1)
                else:
                    print(f"❌ 第 {current_page} 页超过最大重试次数，停止翻页")
                    has_more_data = False

    print(f"\n===== 所有数据获取完成 =====")
    print(f"共获取 {len(all_results)} 条数据")

    # 保存所有数据到文件
    if SAVE_TO_FILE and all_results:
        save_to_json(all_results)
