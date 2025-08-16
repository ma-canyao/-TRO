# 拾贝 TRO 数据抓取与解密脚本

本项目用于从 TRO 平台接口抓取品牌案件列表与详情数据，并对接口返回的加密内容执行 AES-CBC 解密，最终按页输出摘要并可选择保存为 JSON 文件。

> 仅供学习与技术研究使用，请确保在符合目标网站服务条款与当地法律法规的前提下使用。本项目不对任何不当使用承担责任。

---

## 功能特性
- 列表接口抓取：按页请求 `queryTroSearchList` 列表数据。
- AES-CBC 解密：对返回的 Base64 加密数据进行解密与 PKCS7 去填充。
- 列表字段解析：提取案件号、原告、原告律所、涉案知识产权、起诉类型、起诉日等关键信息。
- 详情接口抓取（可选）：基于 `brand_id` 请求 `getBrand`，额外提取版权编号、权利人简介以及相关图片/材料链接。
- 断页与重试：支持最大重试次数与翻页停止条件，避免请求失败导致流程中断。
- 结果落盘（可选）：将所有页聚合的数据保存到 `brand_info.json`。

---

## 目录结构
```
拾贝TRO/
  ├─ main.py            # 主脚本
  └─ README.md          # 使用说明（本文件）
```

---

## 环境要求
- Python 3.8+
- 支持的操作系统：Windows、macOS、Linux（示例命令以 Windows PowerShell 为主）

### 依赖库
- requests
- pycryptodome（提供 `Crypto.Cipher` 的 AES 实现）

安装依赖示例：
```powershell
# 建议使用虚拟环境（可选）
py -m venv .venv
. .venv\Scripts\Activate.ps1

# 安装依赖
pip install requests pycryptodome
```

> 如果你使用的是 CMD，请将激活命令改为：`.venv\Scripts\activate.bat`

---

## 快速开始
1. 进入项目目录：
```powershell
cd 拾贝TRO
```
2. 安装依赖（见上）：
```powershell
pip install requests pycryptodome
```
3. 运行：
```powershell
python .\main.py
```
4. 查看输出：
- 终端将按页打印摘要信息。
- 如启用保存功能，脚本结束后会在当前目录生成 `brand_info.json`。

---

## 运行参数与配置
所有配置均在 `main.py` 顶部或 `__main__` 入口内设置：

### 接口与加解密配置
- `LIST_API_URL`：列表接口 `https://tro.ipsebe.com/api/TroSearch/queryTroSearchList`
- `DETAIL_API_URL`：详情接口 `https://tro.ipsebe.com/api/TroSearch/getBrand`
- `KEY`：16 字节 AES 密钥（示例：`1234567890abddef`）
- `IV`：16 字节初始向量（示例：`absebe1234567890`）
- `headers`：HTTP 请求头（含 `User-Agent`、`Origin`、`Referer` 等）

> 注意：AES 密钥与 IV 必须均为 16 字节；若需替换，请保证长度正确且与服务端保持一致。

### 核心流程配置（在 `if __name__ == "__main__":` 中）
- `START_PAGE`：起始页码，默认 `1`
- `LIMIT`：每页条数，默认 `20`
- `FETCH_DETAILS`：是否抓取详情（`True`/`False`），默认 `True`
- `SAVE_TO_FILE`：是否保存聚合结果到 `brand_info.json`，默认 `True`
- `MAX_RETRY`：单页最大重试次数，默认 `3`
- `DELAY_BETWEEN_PAGES`：翻页之间的延迟秒数，默认 `0.5`

### 核心流程说明
- `fetch_and_decrypt(page, limit, fetch_details)`：
  - 调用列表接口 → 解密数据 → 解析关键信息 →（可选）逐条拉取详情。
- `fetch_brand_details(brand_id)`：
  - 调用详情接口 → 解密 → 仅提取 `plaintiffIntroduction`、`brandCode` 与相关链接。
- `save_to_json(data, filename)`：保存结果为 UTF-8 JSON 文件。

---

## 输出示例
控制台输出会显示每页的摘要，例如：
```
===== 第 1 页 条目 1 =====
案件号: XXXXXX
原告律所: 某某律师事务所
原告: 某公司
涉案知识产权: 某品牌
起诉类型: 侵权
起诉日: 2025-01-01
版权号码: 12345678（若抓取详情）
...（相关链接列表）
```

如启用保存功能，`brand_info.json` 将包含聚合后的结构化数据数组（UTF-8 编码，`ensure_ascii=False`，`indent=2`）。

---

## 常见问题（FAQ）
- Q：运行时报 `ModuleNotFoundError: No module named 'Crypto'`？
  - A：请确认已安装 `pycryptodome`，且未与历史的 `pycrypto` 冲突。可执行：`pip uninstall crypto pycrypto`，然后 `pip install pycryptodome`。
- Q：提示“密钥和初始向量必须为16字节长度”？
  - A：请检查 `KEY` 与 `IV` 的长度是否均为 16 字节，且未包含多余空格或不可见字符。
- Q：请求失败或超时？
  - A：检查网络、接口可用性与 `headers` 是否需要更新；可适当增大 `MAX_RETRY` 与 `DELAY_BETWEEN_PAGES`。
- Q：详情为空或部分字段缺失？
  - A：脚本对缺失字段有健壮处理；详情抓取依赖 `brand_id`，若列表返回不稳定或字段变更，需相应适配解析逻辑。

---

## 合规与免责声明
- 本项目仅用于学习、测试与研究目的，不得用于任何商业或非法用途。
- 若目标平台接口、字段或安全策略发生变更，需自行承担维护成本并确保符合法律法规与服务条款。
- 若你是数据权利方且认为本项目存在不当之处，请联系移除或整改。

---

## 贡献与维护
当前仓库以个人/内部使用为主，欢迎提出 Issue/建议。提交 PR 前请确保：
- 代码可运行且通过基础测试；
- 不引入不必要的依赖；
- 变更点有清晰说明与必要注释。

---

## 许可证
未明确指定。默认视为保留所有权利（All Rights Reserved）。如需开源授权，请在提交前补充相应 LICENSE。
