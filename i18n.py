# -*- coding: utf-8 -*-
"""Small, dependency-free localization layer for PC Context Builder."""

from __future__ import annotations

import json
import locale
import os
import re
from pathlib import Path
from tkinter import ttk

LANGUAGE_NAMES = {
    "zh": "简体中文",
    "ja": "日本語",
    "ko": "한국어",
    "en": "English",
}
LANGUAGE_CODES_BY_NAME = {value: key for key, value in LANGUAGE_NAMES.items()}
LANGUAGE_ORDER = ("zh", "ja", "ko", "en")


# Source strings are Japanese UI copy. The same lookup table also includes
# the English source phrases used by the generated AI-facing README.
TRANSLATIONS = {
    "zh": {
        "言語 / Language": "界面语言",
        "スキャン開始前です。": "尚未开始扫描。",
        "メタデータ一覧を確認してください。": "请检查元数据列表。",
        "収集結果の確認と梱包対象の選択": "检查扫描结果并选择要打包的内容",
        "スキャン対象ドライブの選択": "选择扫描目标驱动器",
        "スキャンするローカル固定ドライブを選択してください。": "请选择要扫描的本地固定驱动器。",
        "ローカル固定ドライブのみを表示します。ネットワークドライブやリムーバブルドライブは通常対象外です。USB SSDなどでもWindowsが固定ドライブとして報告する場合は表示されます。": "此处仅显示本地固定驱动器。网络驱动器和可移动驱动器通常不在扫描范围内。即使是 USB SSD，只要 Windows 将其报告为固定驱动器，也会显示在此处。",
        "キャンセル": "取消",
        "この範囲でスキャン": "扫描所选范围",
        "対象ドライブなし": "未选择驱动器",
        "少なくとも1つのドライブを選択してください。": "请至少选择一个驱动器。",
        "終了確認": "退出确认",
        "スキャン中です。停止してアプリを終了しますか？": "扫描正在进行。要停止扫描并退出应用程序吗？",
        "スキャンを停止して終了しています...": "正在停止扫描并退出……",
        "PC Context Builder": "PC Context Builder",
        "Windows PCの環境情報を収集し、確認後にAIアシスタント向けコンテキストパッケージを作成します。": "收集 Windows 电脑的环境信息，经确认后生成供 AI 助手使用的上下文资料包。",
        "ローカル処理": "本地处理",
        "読み取り専用": "只读",
        "ファイル本文は取得しない": "不读取文件内容",
        "今回のスキャン範囲": "本次扫描范围",
        "Windows・CPU・メモリ・GPU・ディスプレイ情報": "Windows、CPU、内存、GPU 和显示器信息",
        "インストール済みソフトウェア・Python環境・ブラウザー情報": "已安装软件、Python 环境和浏览器信息",
        "ローカル固定ドライブの容量情報": "本地固定驱动器容量信息",
        "ファイル名・パス・サイズ・更新日時（内容は読まない）": "文件名、路径、大小和修改时间（不读取文件内容）",
        "保護領域・資格情報候補・隠しフォルダー・リンク先は除外": "排除受保护区域、可能包含凭据的目录、隐藏文件夹和链接目标",
        "プライバシー保護": "隐私保护",
        "スキャンとZIP生成はPC内で実行します。自動アップロードやネットワーク送信は行いません。ファイル名・パスも個人情報になり得るため、収集結果を確認してから梱包してください。": "扫描和 ZIP 生成均在本机完成，不会自动上传或通过网络发送数据。文件名和路径也可能包含个人信息，请检查扫描结果后再进行打包。",
        "PC全体の概要をスキャン": "扫描电脑概况",
        "スキャンを停止": "停止扫描",
        "重要な注意": "重要提示",
        "• スキャン前に許可を求め、結果一覧の確認と最終承認が終わるまでZIPを作成しません。\n• スキャンは最大10分、最大150,000ファイル・30,000フォルダーで上限を設けます。上限に達した場合は部分スキャンとして記録します。\n• 生成ZIPは通常のZIPです。暗号化されていないため、共有する前に内容を確認してください。": "• 扫描前会征求许可；在检查结果并最终确认之前，不会生成 ZIP。\n• 扫描最长 10 分钟，最多处理 150,000 个文件和 30,000 个文件夹。达到上限时会将结果标记为部分扫描。\n• 生成的 ZIP 不带加密。分享前请检查其中的内容。",
        "スキャン開始前です。": "尚未开始扫描。",
        "システム構成を取得しています...": "正在获取系统配置……",
        "ローカル固定ドライブを確認しています...": "正在检查本地固定驱动器……",
        "スキャンを開始しています...": "正在启动扫描……",
        "停止要求を送信しました。現在の項目を安全に終了しています...": "已发送停止请求，正在安全地完成当前项目……",
        "スキャンをキャンセルしました。ZIPは作成していません。": "已取消扫描，未生成 ZIP。",
        "スキャンが終了しました。収集結果を確認してください。": "扫描已完成，请检查收集结果。",
        "スキャンに失敗しました。": "扫描失败。",
        "スキャン結果のレビュー": "扫描结果审核",
        "注意：スキャンは部分完了です。ZIPのREADMEとscan_reportに未取得範囲が記録されます。": "注意：扫描仅部分完成。未能获取的范围会记录在 ZIP 的 README 和 scan_report 中。",
        "閉じる（梱包しない）": "关闭（不打包）",
        "梱包内容を確認してZIP作成へ": "检查打包内容并创建 ZIP",
        "PC概要": "电脑概况",
        "PC基本情報を梱包する": "打包电脑基本信息",
        "メーカー・モデル": "制造商／型号",
        "マザーボード": "主板",
        "メモリ": "内存",
        "ディスプレイ": "显示器",
        "項目": "项目",
        "取得値": "获取值",
        "コンピューター名とユーザー名を含むパスは匿名化します。機器固有IDやシリアル番号は取得しません。": "包含计算机名和用户名的路径会进行匿名化处理。不会收集设备唯一 ID 或序列号。",
        "ソフトウェア": "软件",
        "アプリ名・発行元・バージョンを検索できます。初期状態ではすべて除外され、選択した行だけがZIPに入ります。": "可以搜索应用名称、发布者和版本。默认全部排除，只有手动选择的条目才会进入 ZIP。",
        "アプリ検索：": "搜索应用：",
        "表示ページをすべて含める": "包含当前页全部项目",
        "表示ページをすべて除外": "排除当前页全部项目",
        "前へ": "上一页",
        "次へ": "下一页",
        "梱包": "打包",
        "アプリ名": "应用名称",
        "バージョン": "版本",
        "発行元": "发布者",
        "インストール先（匿名化）": "安装位置（匿名化）",
        "はい": "是",
        "いいえ": "否",
        "ストレージ": "存储",
        "ドライブ": "驱动器",
        "ボリューム名": "卷标",
        "ファイルシステム": "文件系统",
        "総容量": "总容量",
        "空き容量": "可用空间",
        "ファイル構造": "文件结构",
        "ファイル名・パス等のメタデータを梱包": "打包文件名、路径等元数据",
        "ファイル名・パスには個人情報が含まれる可能性があります。機微候補は初期状態で除外されます。行をダブルクリックすると梱包対象を切り替えます。": "文件名和路径可能包含个人信息。疑似敏感项目默认排除。双击行可切换是否打包。",
        "フォルダー検索：": "搜索文件夹：",
        "フォルダー（匿名化）": "文件夹（匿名化）",
        "階層": "层级",
        "ページ移動で全件を確認できます（1ページ 250 件）。行をダブルクリックすると個別に含める／除外を切り替えます。": "可通过翻页查看全部项目（每页 250 条）。双击某一行可单独切换包含／排除。",
        "名前・パス検索：": "搜索名称／路径：",
        "名前": "名称",
        "拡張子": "扩展名",
        "サイズ": "大小",
        "更新日時": "修改时间",
        "機微候補": "疑似敏感项",
        "パス（匿名化）": "路径（匿名化）",
        "除外・未取得": "已排除／未获取",
        "スキャン警告を梱包する": "打包扫描警告",
        "スキップされた項目：": "已跳过项目：",
        "アクセス／メタデータ取得エラー：": "访问／元数据获取错误：",
        "ファイル：": "文件：",
        "フォルダー：": "文件夹：",
        "スキャン状態：": "扫描状态：",
        "OS・アプリケーションの保護領域、隠し／システムフォルダー、資格情報候補のフォルダー、再解析ポイントは走査しません。": "不会扫描操作系统或应用程序保护区域、隐藏／系统文件夹、疑似凭据目录和重解析点。",
        "スキャン警告CSVにはドライブ文字とエラー種別だけを記録します。個別のファイルパスは出力しません。": "扫描警告 CSV 仅记录驱动器盘符和错误类型，不会输出具体文件路径。",
        "梱包対象なし": "没有选择打包内容",
        "少なくとも1つのカテゴリを選択してください。": "请至少选择一个类别。",
        "最終確認": "最终确认",
        "機微候補の最終確認": "疑似敏感项目最终确认",
        "警告：機微候補として検出されたファイル名が": "警告：检测到疑似敏感文件名，数量为",
        "この内容で続行しますか？": "要按此内容继续吗？",
        "スキャン対象ドライブの選択": "选择扫描目标驱动器",
        "この機能はWindows上で実行してください。": "此功能必须在 Windows 上运行。",
        "Windows PowerShell が見つかりません。": "找不到 Windows PowerShell。",
        "PowerShell CIM取得に失敗しました。": "PowerShell CIM 信息获取失败。",
        "PowerShellから空の結果が返されました。": "PowerShell 返回了空结果。",
        "ファイル構造スキャンの結果を取得できませんでした。": "无法获取文件结构扫描结果。",
        "Windows専用": "仅支持 Windows",
        "このアプリはWindows 11上で実行してください。": "请在 Windows 11 上运行此应用程序。",
        "実行環境が違います": "运行环境不匹配",
        "Python 3.14 x64が必要です。": "需要 Python 3.14 x64。",
        "スキャン開始の確認": "扫描开始确认",
        "ローカルPCのシステム情報・ソフトウェア情報・ドライブ情報・ファイルのメタデータを読み取り専用で調査します。\n\nファイルの中身、パスワード、Cookie、APIキーは読み取りません。\n\n続けて対象ドライブを選択します。開始しますか？": "将以只读方式检查本地电脑的系统信息、软件信息、驱动器信息和文件元数据。\n\n不会读取文件内容、密码、Cookie 或 API 密钥。\n\n接下来将选择目标驱动器。现在开始吗？",
        "ドライブを検出できません": "无法检测驱动器",
        "ローカル固定ドライブを取得できませんでした。": "无法获取本地固定驱动器。",
        "AI向けZIPの出力先を選択してください": "请选择 AI 资料 ZIP 的输出位置",
        "キャンセル": "取消",
        "出力先が選択されなかったため、ZIPは作成していません。レビュー画面に戻ります。": "由于未选择输出位置，因此未创建 ZIP。返回审核窗口。",
        "AI向けZIPを作成し、整合性を検査しています...": "正在创建 AI 资料 ZIP 并检查完整性……",
        "ZIPの作成と整合性検査が完了しました。": "ZIP 创建及完整性检查已完成。",
        "作成完了": "创建完成",
        "AI向けZIPを作成しました。": "已创建 AI 资料 ZIP。",
        "ZIPの中身を確認してからAIアシスタントに共有してください。": "请先检查 ZIP 内容，再分享给 AI 助手。",
        "ZIPの作成に失敗しました。": "ZIP 创建失败。",
        "ZIP作成エラー": "ZIP 创建错误",
        "Windows 11 only": "仅支持 Windows 11",
        # English source text in the generated README
        "PC Context Pack": "PC 上下文资料包",
        "Schema version": "架构版本",
        "Scan time": "扫描时间",
        "Collection method: local read-only inventory": "收集方式：本地只读清单",
        "Network upload: not performed": "网络上传：未执行",
        "File contents: NOT collected or copied": "文件内容：未收集或复制",
        "Machine and user path masking: applied where supported": "设备与用户路径匿名化：在支持的情况下已应用",
        "PC overview": "电脑概览",
        "Included categories": "包含的类别",
        "PC profile": "电脑基本信息",
        "Installed software": "已安装软件",
        "Storage": "存储",
        "Folder index": "文件夹索引",
        "File metadata index": "文件元数据索引",
        "Scan warnings": "扫描警告",
        "Security/exclusion summary": "安全／排除项摘要",
        "included": "已包含",
        "not included": "未包含",
        "Privacy and interpretation": "隐私与数据说明",
        "This package contains inventory metadata only. It does not include document text, image pixels, video/audio contents, browser history, cookies, saved passwords, API keys, tokens, SSH private keys, or Windows credentials.": "此资料包仅包含清单元数据，不包含文档正文、图像像素、视频／音频内容、浏览历史、Cookie、已保存密码、API 密钥、令牌、SSH 私钥或 Windows 凭据。",
        "File and folder names can still reveal personal information. Review this package before sharing it. Candidate sensitive names are excluded by default, but heuristic detection is not perfect.": "文件和文件夹名称仍可能泄露个人信息。分享前请检查此资料包。疑似敏感名称默认排除，但启发式检测并不能保证万无一失。",
        "Paths under the current user profile are represented with %USERPROFILE% where detected. Some third-party software paths may still contain identifying details.": "检测到当前用户配置文件目录时，会以 %USERPROFILE% 替代。部分第三方软件路径仍可能包含可识别信息。",
        "System/application directories, common cloud-sync folders, hidden/system files and folders, reparse points, caches, and known credential folders were excluded from the file-system walk.": "文件系统扫描会排除系统／应用程序目录、常见云同步文件夹、隐藏／系统文件和文件夹、重解析点、缓存以及已知凭据目录。",
        "Software names, folder paths, and file metadata are opt-in: their rows are excluded by default until individually selected in the review window.": "软件名称、文件夹路径和文件元数据均需主动选择：默认排除，只有在审核窗口中单独选择后才会纳入。",
        "A partial scan or access errors mean the inventory is incomplete. See scan_report.json and warnings.csv.": "部分扫描或访问错误意味着清单不完整。请查看 scan_report.json 和 warnings.csv。",
        "How an AI assistant should use this package": "AI 助手应如何使用此资料包",
        "Use system_profile.json to understand the machine environment; installed_software.csv to identify selected software; volumes.csv for storage; folders.csv and files.csv as a searchable metadata index only. Do not assume the package contains file contents.": "使用 system_profile.json 了解电脑环境；使用 installed_software.csv 查看已选择的软件；使用 volumes.csv 查看存储信息；folders.csv 和 files.csv 仅是可搜索的元数据索引。不要假定资料包中包含文件内容。",
    },
    "ja": {
        "言語 / Language": "言語",
        "PC Context Pack": "PC コンテキストパック",
        "Schema version": "スキーマバージョン",
        "Scan time": "スキャン時刻",
        "Collection method: local read-only inventory": "収集方法：ローカル読み取り専用インベントリ",
        "Network upload: not performed": "ネットワークへのアップロード：未実施",
        "File contents: NOT collected or copied": "ファイル内容：収集・コピーしていません",
        "Machine and user path masking: applied where supported": "端末・ユーザーパスのマスキング：対応可能な範囲で適用",
        "PC overview": "PC概要",
        "Included categories": "収録カテゴリ",
        "PC profile": "PC基本情報",
        "Installed software": "インストール済みソフトウェア",
        "Storage": "ストレージ",
        "Folder index": "フォルダー索引",
        "File metadata index": "ファイルメタデータ索引",
        "Scan warnings": "スキャン警告",
        "Security/exclusion summary": "セキュリティ／除外サマリー",
        "included": "含む",
        "not included": "含まない",
        "Privacy and interpretation": "プライバシーと解釈",
        "This package contains inventory metadata only. It does not include document text, image pixels, video/audio contents, browser history, cookies, saved passwords, API keys, tokens, SSH private keys, or Windows credentials.": "このパッケージにはインベントリのメタデータのみが含まれます。文書本文、画像ピクセル、動画・音声の内容、ブラウザー履歴、Cookie、保存済みパスワード、APIキー、トークン、SSH秘密鍵、Windows資格情報は含まれません。",
        "File and folder names can still reveal personal information. Review this package before sharing it. Candidate sensitive names are excluded by default, but heuristic detection is not perfect.": "ファイル名やフォルダー名から個人情報が分かる場合があります。共有前に内容を確認してください。機微情報の候補は初期状態で除外されますが、ヒューリスティック検出は完全ではありません。",
        "Paths under the current user profile are represented with %USERPROFILE% where detected. Some third-party software paths may still contain identifying details.": "現在のユーザープロファイル配下のパスは、検出できた場合に %USERPROFILE% として表記します。一部のサードパーティ製ソフトウェアのパスには識別情報が残る場合があります。",
        "System/application directories, common cloud-sync folders, hidden/system files and folders, reparse points, caches, and known credential folders were excluded from the file-system walk.": "ファイルシステムの走査では、システム／アプリケーションディレクトリ、一般的なクラウド同期フォルダー、隠し／システムファイルとフォルダー、再解析ポイント、キャッシュ、既知の資格情報フォルダーを除外しました。",
        "Software names, folder paths, and file metadata are opt-in: their rows are excluded by default until individually selected in the review window.": "ソフトウェア名、フォルダーパス、ファイルメタデータは任意選択です。レビュー画面で個別に選択するまで、初期状態では除外されます。",
        "A partial scan or access errors mean the inventory is incomplete. See scan_report.json and warnings.csv.": "部分スキャンやアクセスエラーがある場合、インベントリは不完全です。scan_report.json と warnings.csv を確認してください。",
        "How an AI assistant should use this package": "AIアシスタントによるこのパッケージの利用方法",
        "Use system_profile.json to understand the machine environment; installed_software.csv to identify selected software; volumes.csv for storage; folders.csv and files.csv as a searchable metadata index only. Do not assume the package contains file contents.": "system_profile.json でPC環境を把握し、installed_software.csv で選択済みソフトウェアを確認し、volumes.csv でストレージを確認します。folders.csv と files.csv は検索可能なメタデータ索引としてのみ使用してください。パッケージにファイル本文が含まれると想定しないでください。",
    },
    "ko": {
        "言語 / Language": "언어",
        "スキャン開始前です。": "스캔을 시작하기 전입니다.",
        "メタデータ一覧を確認してください。": "메타데이터 목록을 확인하세요.",
        "収集結果の確認と梱包対象の選択": "수집 결과 확인 및 패키징 항목 선택",
        "スキャン対象ドライブの選択": "스캔할 드라이브 선택",
        "スキャンするローカル固定ドライブを選択してください。": "스캔할 로컬 고정 드라이브를 선택하세요.",
        "ローカル固定ドライブのみを表示します。ネットワークドライブやリムーバブルドライブは通常対象外です。USB SSDなどでもWindowsが固定ドライブとして報告する場合は表示されます。": "로컬 고정 드라이브만 표시합니다. 네트워크 드라이브와 이동식 드라이브는 일반적으로 대상에서 제외됩니다. USB SSD라도 Windows에서 고정 드라이브로 보고하면 표시됩니다.",
        "キャンセル": "취소",
        "この範囲でスキャン": "선택한 범위 스캔",
        "対象ドライブなし": "드라이브가 선택되지 않음",
        "少なくとも1つのドライブを選択してください。": "드라이브를 하나 이상 선택하세요.",
        "終了確認": "종료 확인",
        "スキャン中です。停止してアプリを終了しますか？": "스캔이 진행 중입니다. 스캔을 중지하고 앱을 종료할까요?",
        "スキャンを停止して終了しています...": "스캔을 중지하고 종료하는 중...",
        "PC Context Builder": "PC Context Builder",
        "Windows PCの環境情報を収集し、確認後にAIアシスタント向けコンテキストパッケージを作成します。": "Windows PC 환경 정보를 수집하고 검토한 후 AI 어시스턴트용 컨텍스트 패키지를 만듭니다.",
        "ローカル処理": "로컬 처리",
        "読み取り専用": "읽기 전용",
        "ファイル本文は取得しない": "파일 내용은 수집하지 않음",
        "今回のスキャン範囲": "이번 스캔 범위",
        "Windows・CPU・メモリ・GPU・ディスプレイ情報": "Windows, CPU, 메모리, GPU 및 디스플레이 정보",
        "インストール済みソフトウェア・Python環境・ブラウザー情報": "설치된 소프트웨어, Python 환경 및 브라우저 정보",
        "ローカル固定ドライブの容量情報": "로컬 고정 드라이브 용량 정보",
        "ファイル名・パス・サイズ・更新日時（内容は読まない）": "파일 이름, 경로, 크기 및 수정 시간(내용은 읽지 않음)",
        "保護領域・資格情報候補・隠しフォルダー・リンク先は除外": "보호 영역, 자격 증명 후보, 숨김 폴더 및 링크 대상 제외",
        "プライバシー保護": "개인정보 보호",
        "スキャンとZIP生成はPC内で実行します。自動アップロードやネットワーク送信は行いません。ファイル名・パスも個人情報になり得るため、収集結果を確認してから梱包してください。": "스캔과 ZIP 생성은 PC 내부에서 실행됩니다. 자동 업로드나 네트워크 전송은 하지 않습니다. 파일 이름과 경로에도 개인정보가 포함될 수 있으므로 수집 결과를 확인한 후 패키징하세요.",
        "PC全体の概要をスキャン": "PC 전체 개요 스캔",
        "スキャンを停止": "스캔 중지",
        "重要な注意": "중요 안내",
        "• スキャン前に許可を求め、結果一覧の確認と最終承認が終わるまでZIPを作成しません。\n• スキャンは最大10分、最大150,000ファイル・30,000フォルダーで上限を設けます。上限に達した場合は部分スキャンとして記録します。\n• 生成ZIPは通常のZIPです。暗号化されていないため、共有する前に内容を確認してください。": "• 스캔 전에 허가를 요청하며 결과 목록 검토와 최종 승인 전에는 ZIP을 만들지 않습니다.\n• 스캔은 최대 10분, 파일 150,000개 및 폴더 30,000개로 제한됩니다. 한도에 도달하면 부분 스캔으로 기록합니다.\n• 생성된 ZIP은 일반 ZIP이며 암호화되지 않습니다. 공유 전에 내용을 확인하세요.",
        "システム構成を取得しています...": "시스템 구성을 가져오는 중...",
        "ローカル固定ドライブを確認しています...": "로컬 고정 드라이브를 확인하는 중...",
        "スキャンを開始しています...": "스캔을 시작하는 중...",
        "停止要求を送信しました。現在の項目を安全に終了しています...": "중지 요청을 보냈습니다. 현재 항목을 안전하게 마무리하는 중...",
        "スキャンをキャンセルしました。ZIPは作成していません。": "스캔이 취소되었습니다. ZIP은 생성하지 않았습니다.",
        "スキャンが終了しました。収集結果を確認してください。": "스캔이 완료되었습니다. 수집 결과를 확인하세요.",
        "スキャンに失敗しました。": "스캔에 실패했습니다.",
        "スキャン結果のレビュー": "스캔 결과 검토",
        "注意：スキャンは部分完了です。ZIPのREADMEとscan_reportに未取得範囲が記録されます。": "주의: 스캔이 부분적으로 완료되었습니다. 가져오지 못한 범위는 ZIP의 README와 scan_report에 기록됩니다.",
        "閉じる（梱包しない）": "닫기(패키징 안 함)",
        "梱包内容を確認してZIP作成へ": "패키지 내용 확인 후 ZIP 만들기",
        "PC概要": "PC 개요",
        "PC基本情報を梱包する": "PC 기본 정보 패키징",
        "メーカー・モデル": "제조사 / 모델",
        "マザーボード": "마더보드",
        "メモリ": "메모리",
        "ディスプレイ": "디스플레이",
        "項目": "항목",
        "取得値": "가져온 값",
        "コンピューター名とユーザー名を含むパスは匿名化します。機器固有IDやシリアル番号は取得しません。": "컴퓨터 이름과 사용자 이름이 포함된 경로는 익명화합니다. 장치 고유 ID나 일련 번호는 수집하지 않습니다.",
        "ソフトウェア": "소프트웨어",
        "アプリ名・発行元・バージョンを検索できます。初期状態ではすべて除外され、選択した行だけがZIPに入ります。": "앱 이름, 게시자 및 버전을 검색할 수 있습니다. 기본적으로 모두 제외되며 선택한 행만 ZIP에 포함됩니다.",
        "アプリ検索：": "앱 검색:",
        "表示ページをすべて含める": "현재 페이지 모두 포함",
        "表示ページをすべて除外": "현재 페이지 모두 제외",
        "前へ": "이전",
        "次へ": "다음",
        "梱包": "포함",
        "アプリ名": "앱 이름",
        "バージョン": "버전",
        "発行元": "게시자",
        "インストール先（匿名化）": "설치 위치(익명화)",
        "はい": "예",
        "いいえ": "아니요",
        "ストレージ": "저장소",
        "ドライブ": "드라이브",
        "ボリューム名": "볼륨 이름",
        "ファイルシステム": "파일 시스템",
        "総容量": "전체 용량",
        "空き容量": "사용 가능 공간",
        "ファイル構造": "파일 구조",
        "ファイル名・パス等のメタデータを梱包": "파일 이름, 경로 등의 메타데이터 패키징",
        "ファイル名・パスには個人情報が含まれる可能性があります。機微候補は初期状態で除外されます。行をダブルクリックすると梱包対象を切り替えます。": "파일 이름과 경로에 개인정보가 포함될 수 있습니다. 민감 정보 후보는 기본적으로 제외됩니다. 행을 두 번 클릭하면 포함 여부를 전환합니다.",
        "フォルダー検索：": "폴더 검색:",
        "フォルダー（匿名化）": "폴더(익명화)",
        "階層": "깊이",
        "ページ移動で全件を確認できます（1ページ 250 件）。行をダブルクリックすると個別に含める／除外を切り替えます。": "페이지를 이동해 모든 항목을 확인할 수 있습니다(페이지당 250개). 행을 두 번 클릭하면 개별 포함 여부를 전환합니다.",
        "名前・パス検索：": "이름 / 경로 검색:",
        "名前": "이름",
        "拡張子": "확장자",
        "サイズ": "크기",
        "更新日時": "수정 시간",
        "機微候補": "민감 정보 후보",
        "パス（匿名化）": "경로(익명화)",
        "除外・未取得": "제외 / 미수집",
        "スキャン警告を梱包する": "스캔 경고 패키징",
        "スキップされた項目：": "건너뛴 항목:",
        "アクセス／メタデータ取得エラー：": "접근 / 메타데이터 수집 오류:",
        "ファイル：": "파일:",
        "フォルダー：": "폴더:",
        "スキャン状態：": "스캔 상태:",
        "OS・アプリケーションの保護領域、隠し／システムフォルダー、資格情報候補のフォルダー、再解析ポイントは走査しません。": "OS 및 애플리케이션 보호 영역, 숨김 / 시스템 폴더, 자격 증명 후보 폴더, 재분석 지점은 스캔하지 않습니다.",
        "スキャン警告CSVにはドライブ文字とエラー種別だけを記録します。個別のファイルパスは出力しません。": "스캔 경고 CSV에는 드라이브 문자와 오류 유형만 기록합니다. 개별 파일 경로는 출력하지 않습니다.",
        "梱包対象なし": "패키징 항목 없음",
        "少なくとも1つのカテゴリを選択してください。": "범주를 하나 이상 선택하세요.",
        "最終確認": "최종 확인",
        "機微候補の最終確認": "민감 정보 후보 최종 확인",
        "この内容で続行しますか？": "이 내용으로 계속할까요?",
        "Windows専用": "Windows 전용",
        "このアプリはWindows 11上で実行してください。": "이 앱은 Windows 11에서 실행하세요.",
        "実行環境が違います": "실행 환경이 올바르지 않음",
        "Python 3.14 x64が必要です。": "Python 3.14 x64가 필요합니다.",
        "スキャン開始の確認": "스캔 시작 확인",
        "ローカルPCのシステム情報・ソフトウェア情報・ドライブ情報・ファイルのメタデータを読み取り専用で調査します。\n\nファイルの中身、パスワード、Cookie、APIキーは読み取りません。\n\n続けて対象ドライブを選択します。開始しますか？": "로컬 PC의 시스템 정보, 소프트웨어 정보, 드라이브 정보 및 파일 메타데이터를 읽기 전용으로 조사합니다.\n\n파일 내용, 비밀번호, Cookie 또는 API 키는 읽지 않습니다.\n\n계속해서 대상 드라이브를 선택합니다. 시작할까요?",
        "ドライブを検出できません": "드라이브를 찾을 수 없음",
        "ローカル固定ドライブを取得できませんでした。": "로컬 고정 드라이브를 가져오지 못했습니다.",
        "AI向けZIPの出力先を選択してください": "AI용 ZIP을 저장할 위치를 선택하세요.",
        "出力先が選択されなかったため、ZIPは作成していません。レビュー画面に戻ります。": "저장 위치를 선택하지 않아 ZIP을 만들지 않았습니다. 검토 화면으로 돌아갑니다.",
        "AI向けZIPを作成し、整合性を検査しています...": "AI용 ZIP을 만들고 무결성을 검사하는 중...",
        "ZIPの作成と整合性検査が完了しました。": "ZIP 생성 및 무결성 검사가 완료되었습니다.",
        "作成完了": "생성 완료",
        "AI向けZIPを作成しました。": "AI용 ZIP을 만들었습니다.",
        "ZIPの中身を確認してからAIアシスタントに共有してください。": "ZIP 내용을 확인한 후 AI 어시스턴트와 공유하세요.",
        "ZIPの作成に失敗しました。": "ZIP 생성에 실패했습니다.",
        "ZIP作成エラー": "ZIP 생성 오류",
        "Windows 11 only": "Windows 11 전용",
        # English source text in the generated README
        "PC Context Pack": "PC 컨텍스트 패키지",
        "Schema version": "스키마 버전",
        "Scan time": "스캔 시간",
        "Collection method: local read-only inventory": "수집 방식: 로컬 읽기 전용 인벤토리",
        "Network upload: not performed": "네트워크 업로드: 수행하지 않음",
        "File contents: NOT collected or copied": "파일 내용: 수집하거나 복사하지 않음",
        "Machine and user path masking: applied where supported": "장치 및 사용자 경로 마스킹: 지원되는 경우 적용",
        "PC overview": "PC 개요",
        "Included categories": "포함된 범주",
        "PC profile": "PC 기본 정보",
        "Installed software": "설치된 소프트웨어",
        "Storage": "저장소",
        "Folder index": "폴더 색인",
        "File metadata index": "파일 메타데이터 색인",
        "Scan warnings": "스캔 경고",
        "Security/exclusion summary": "보안 / 제외 요약",
        "included": "포함",
        "not included": "포함 안 됨",
        "Privacy and interpretation": "개인정보 보호 및 해석",
        "This package contains inventory metadata only. It does not include document text, image pixels, video/audio contents, browser history, cookies, saved passwords, API keys, tokens, SSH private keys, or Windows credentials.": "이 패키지에는 인벤토리 메타데이터만 포함됩니다. 문서 본문, 이미지 픽셀, 동영상 / 오디오 내용, 브라우저 기록, 쿠키, 저장된 비밀번호, API 키, 토큰, SSH 개인 키 또는 Windows 자격 증명은 포함되지 않습니다.",
        "File and folder names can still reveal personal information. Review this package before sharing it. Candidate sensitive names are excluded by default, but heuristic detection is not perfect.": "파일 및 폴더 이름만으로도 개인정보가 드러날 수 있습니다. 공유하기 전에 이 패키지를 검토하세요. 민감 정보 후보 이름은 기본적으로 제외되지만 휴리스틱 탐지가 완벽하지는 않습니다.",
        "Paths under the current user profile are represented with %USERPROFILE% where detected. Some third-party software paths may still contain identifying details.": "현재 사용자 프로필 아래의 경로는 감지되는 경우 %USERPROFILE%로 표시합니다. 일부 타사 소프트웨어 경로에는 식별 정보가 남을 수 있습니다.",
        "System/application directories, common cloud-sync folders, hidden/system files and folders, reparse points, caches, and known credential folders were excluded from the file-system walk.": "파일 시스템 탐색에서 시스템 / 애플리케이션 디렉터리, 일반적인 클라우드 동기화 폴더, 숨김 / 시스템 파일과 폴더, 재분석 지점, 캐시 및 알려진 자격 증명 폴더를 제외했습니다.",
        "Software names, folder paths, and file metadata are opt-in: their rows are excluded by default until individually selected in the review window.": "소프트웨어 이름, 폴더 경로 및 파일 메타데이터는 선택 항목입니다. 검토 창에서 개별적으로 선택하기 전까지 기본적으로 제외됩니다.",
        "A partial scan or access errors mean the inventory is incomplete. See scan_report.json and warnings.csv.": "부분 스캔 또는 접근 오류가 있으면 인벤토리가 불완전합니다. scan_report.json 및 warnings.csv를 확인하세요.",
        "How an AI assistant should use this package": "AI 어시스턴트가 이 패키지를 사용하는 방법",
        "Use system_profile.json to understand the machine environment; installed_software.csv to identify selected software; volumes.csv for storage; folders.csv and files.csv as a searchable metadata index only. Do not assume the package contains file contents.": "system_profile.json으로 PC 환경을 파악하고, installed_software.csv로 선택된 소프트웨어를 확인하며, volumes.csv로 저장소를 확인하세요. folders.csv와 files.csv는 검색 가능한 메타데이터 색인으로만 사용해야 합니다. 패키지에 파일 내용이 포함되어 있다고 가정하지 마세요.",
    },
    "en": {
        "言語 / Language": "Language",
        "スキャン開始前です。": "Scan has not started.",
        "メタデータ一覧を確認してください。": "Review the metadata list.",
        "収集結果の確認と梱包対象の選択": "Review scan results and select package contents",
        "スキャン対象ドライブの選択": "Select drives to scan",
        "スキャンするローカル固定ドライブを選択してください。": "Select the local fixed drives to scan.",
        "ローカル固定ドライブのみを表示します。ネットワークドライブやリムーバブルドライブは通常対象外です。USB SSDなどでもWindowsが固定ドライブとして報告する場合は表示されます。": "Only local fixed drives are shown. Network and removable drives are normally excluded. A USB SSD may appear if Windows reports it as a fixed drive.",
        "キャンセル": "Cancel",
        "この範囲でスキャン": "Scan selected drives",
        "対象ドライブなし": "No drive selected",
        "少なくとも1つのドライブを選択してください。": "Select at least one drive.",
        "終了確認": "Confirm exit",
        "スキャン中です。停止してアプリを終了しますか？": "A scan is in progress. Stop the scan and exit the application?",
        "スキャンを停止して終了しています...": "Stopping the scan and exiting...",
        "PC Context Builder": "PC Context Builder",
        "Windows PCの環境情報を収集し、確認後にAIアシスタント向けコンテキストパッケージを作成します。": "Collects Windows PC environment information and creates an AI-assistant context package after your review.",
        "ローカル処理": "Local processing",
        "読み取り専用": "Read-only",
        "ファイル本文は取得しない": "File contents are never read",
        "今回のスキャン範囲": "Scan scope",
        "Windows・CPU・メモリ・GPU・ディスプレイ情報": "Windows, CPU, memory, GPU, and display information",
        "インストール済みソフトウェア・Python環境・ブラウザー情報": "Installed software, Python environments, and browser information",
        "ローカル固定ドライブの容量情報": "Local fixed-drive capacity",
        "ファイル名・パス・サイズ・更新日時（内容は読まない）": "File names, paths, sizes, and modified times (contents are not read)",
        "保護領域・資格情報候補・隠しフォルダー・リンク先は除外": "Protected areas, credential candidates, hidden folders, and link targets are excluded",
        "プライバシー保護": "Privacy protection",
        "スキャンとZIP生成はPC内で実行します。自動アップロードやネットワーク送信は行いません。ファイル名・パスも個人情報になり得るため、収集結果を確認してから梱包してください。": "Scanning and ZIP generation run locally. No automatic upload or network transfer occurs. File names and paths can contain personal information, so review the results before packaging.",
        "PC全体の概要をスキャン": "Scan PC overview",
        "スキャンを停止": "Stop scan",
        "重要な注意": "Important notes",
        "• スキャン前に許可を求め、結果一覧の確認と最終承認が終わるまでZIPを作成しません。\n• スキャンは最大10分、最大150,000ファイル・30,000フォルダーで上限を設けます。上限に達した場合は部分スキャンとして記録します。\n• 生成ZIPは通常のZIPです。暗号化されていないため、共有する前に内容を確認してください。": "• Permission is requested before scanning. No ZIP is created until you review the results and give final approval.\n• Scanning is limited to 10 minutes, 150,000 files, and 30,000 folders. Reaching a limit is recorded as a partial scan.\n• The generated ZIP is not encrypted. Review its contents before sharing.",
        "システム構成を取得しています...": "Collecting system information...",
        "ローカル固定ドライブを確認しています...": "Checking local fixed drives...",
        "スキャンを開始しています...": "Starting scan...",
        "停止要求を送信しました。現在の項目を安全に終了しています...": "Stop requested. Safely finishing the current item...",
        "スキャンをキャンセルしました。ZIPは作成していません。": "Scan cancelled. No ZIP was created.",
        "スキャンが終了しました。収集結果を確認してください。": "Scan finished. Review the collected results.",
        "スキャンに失敗しました。": "Scan failed.",
        "スキャン結果のレビュー": "Scan results review",
        "注意：スキャンは部分完了です。ZIPのREADMEとscan_reportに未取得範囲が記録されます。": "Note: The scan is only partially complete. Uncollected areas are recorded in the ZIP README and scan_report.",
        "閉じる（梱包しない）": "Close (do not package)",
        "梱包内容を確認してZIP作成へ": "Review package contents and create ZIP",
        "PC概要": "PC overview",
        "PC基本情報を梱包する": "Include PC profile",
        "メーカー・モデル": "Manufacturer / model",
        "マザーボード": "Motherboard",
        "メモリ": "Memory",
        "ディスプレイ": "Display",
        "項目": "Item",
        "取得値": "Collected value",
        "コンピューター名とユーザー名を含むパスは匿名化します。機器固有IDやシリアル番号は取得しません。": "Paths containing the computer or user name are anonymized. Device-specific IDs and serial numbers are not collected.",
        "ソフトウェア": "Software",
        "アプリ名・発行元・バージョンを検索できます。初期状態ではすべて除外され、選択した行だけがZIPに入ります。": "Search by app name, publisher, or version. All entries are excluded by default; only selected rows are added to the ZIP.",
        "アプリ検索：": "Search apps:",
        "表示ページをすべて含める": "Include all on this page",
        "表示ページをすべて除外": "Exclude all on this page",
        "前へ": "Previous",
        "次へ": "Next",
        "梱包": "Include",
        "アプリ名": "App name",
        "バージョン": "Version",
        "発行元": "Publisher",
        "インストール先（匿名化）": "Install location (anonymized)",
        "はい": "Yes",
        "いいえ": "No",
        "ストレージ": "Storage",
        "ドライブ": "Drive",
        "ボリューム名": "Volume name",
        "ファイルシステム": "File system",
        "総容量": "Total capacity",
        "空き容量": "Free space",
        "ファイル構造": "File structure",
        "ファイル名・パス等のメタデータを梱包": "Include file-name, path, and other metadata",
        "ファイル名・パスには個人情報が含まれる可能性があります。機微候補は初期状態で除外されます。行をダブルクリックすると梱包対象を切り替えます。": "File names and paths may contain personal information. Sensitive candidates are excluded by default. Double-click a row to toggle inclusion.",
        "フォルダー検索：": "Search folders:",
        "フォルダー（匿名化）": "Folder (anonymized)",
        "階層": "Depth",
        "ページ移動で全件を確認できます（1ページ 250 件）。行をダブルクリックすると個別に含める／除外を切り替えます。": "Use the page controls to review all entries (250 per page). Double-click a row to toggle its inclusion.",
        "名前・パス検索：": "Search names / paths:",
        "名前": "Name",
        "拡張子": "Extension",
        "サイズ": "Size",
        "更新日時": "Modified",
        "機微候補": "Sensitive candidate",
        "パス（匿名化）": "Path (anonymized)",
        "除外・未取得": "Excluded / unavailable",
        "スキャン警告を梱包する": "Include scan warnings",
        "スキップされた項目：": "Skipped items:",
        "アクセス／メタデータ取得エラー：": "Access / metadata errors:",
        "ファイル：": "Files:",
        "フォルダー：": "Folders:",
        "スキャン状態：": "Scan status:",
        "OS・アプリケーションの保護領域、隠し／システムフォルダー、資格情報候補のフォルダー、再解析ポイントは走査しません。": "OS and application-protected areas, hidden/system folders, credential-candidate folders, and reparse points are not scanned.",
        "スキャン警告CSVにはドライブ文字とエラー種別だけを記録します。個別のファイルパスは出力しません。": "The scan-warning CSV records only drive letters and error types. Individual file paths are not exported.",
        "梱包対象なし": "Nothing selected for packaging",
        "少なくとも1つのカテゴリを選択してください。": "Select at least one category.",
        "最終確認": "Final confirmation",
        "機微候補の最終確認": "Final confirmation for sensitive candidates",
        "この内容で続行しますか？": "Continue with these contents?",
        "Windows専用": "Windows only",
        "このアプリはWindows 11上で実行してください。": "Run this application on Windows 11.",
        "実行環境が違います": "Unsupported runtime",
        "Python 3.14 x64が必要です。": "Python 3.14 x64 is required.",
        "スキャン開始の確認": "Confirm scan",
        "ローカルPCのシステム情報・ソフトウェア情報・ドライブ情報・ファイルのメタデータを読み取り専用で調査します。\n\nファイルの中身、パスワード、Cookie、APIキーは読み取りません。\n\n続けて対象ドライブを選択します。開始しますか？": "The application will perform a read-only inspection of local system, software, drive, and file metadata.\n\nIt will not read file contents, passwords, cookies, or API keys.\n\nYou will select the target drives next. Start now?",
        "ドライブを検出できません": "No drives detected",
        "ローカル固定ドライブを取得できませんでした。": "Could not retrieve local fixed drives.",
        "AI向けZIPの出力先を選択してください": "Select the output folder for the AI context ZIP",
        "出力先が選択されなかったため、ZIPは作成していません。レビュー画面に戻ります。": "No output folder was selected, so no ZIP was created. Returning to the review window.",
        "AI向けZIPを作成し、整合性を検査しています...": "Creating the AI context ZIP and checking integrity...",
        "ZIPの作成と整合性検査が完了しました。": "ZIP creation and integrity check completed.",
        "作成完了": "Creation complete",
        "AI向けZIPを作成しました。": "The AI context ZIP was created.",
        "ZIPの中身を確認してからAIアシスタントに共有してください。": "Review the ZIP contents before sharing them with an AI assistant.",
        "ZIPの作成に失敗しました。": "Could not create the ZIP.",
        "ZIP作成エラー": "ZIP creation error",
        "Windows 11 only": "Windows 11 only",
        # English source text in the generated README
        "PC Context Pack": "PC Context Pack",
        "Schema version": "Schema version",
        "Scan time": "Scan time",
        "Collection method: local read-only inventory": "Collection method: local read-only inventory",
        "Network upload: not performed": "Network upload: not performed",
        "File contents: NOT collected or copied": "File contents: NOT collected or copied",
        "Machine and user path masking: applied where supported": "Machine and user path masking: applied where supported",
        "PC overview": "PC overview",
        "Included categories": "Included categories",
        "PC profile": "PC profile",
        "Installed software": "Installed software",
        "Storage": "Storage",
        "Folder index": "Folder index",
        "File metadata index": "File metadata index",
        "Scan warnings": "Scan warnings",
        "Security/exclusion summary": "Security/exclusion summary",
        "included": "included",
        "not included": "not included",
        "Privacy and interpretation": "Privacy and interpretation",
        "This package contains inventory metadata only. It does not include document text, image pixels, video/audio contents, browser history, cookies, saved passwords, API keys, tokens, SSH private keys, or Windows credentials.": "This package contains inventory metadata only. It does not include document text, image pixels, video/audio contents, browser history, cookies, saved passwords, API keys, tokens, SSH private keys, or Windows credentials.",
        "File and folder names can still reveal personal information. Review this package before sharing it. Candidate sensitive names are excluded by default, but heuristic detection is not perfect.": "File and folder names can still reveal personal information. Review this package before sharing it. Candidate sensitive names are excluded by default, but heuristic detection is not perfect.",
        "Paths under the current user profile are represented with %USERPROFILE% where detected. Some third-party software paths may still contain identifying details.": "Paths under the current user profile are represented with %USERPROFILE% where detected. Some third-party software paths may still contain identifying details.",
        "System/application directories, common cloud-sync folders, hidden/system files and folders, reparse points, caches, and known credential folders were excluded from the file-system walk.": "System/application directories, common cloud-sync folders, hidden/system files and folders, reparse points, caches, and known credential folders were excluded from the file-system walk.",
        "Software names, folder paths, and file metadata are opt-in: their rows are excluded by default until individually selected in the review window.": "Software names, folder paths, and file metadata are opt-in: their rows are excluded by default until individually selected in the review window.",
        "A partial scan or access errors mean the inventory is incomplete. See scan_report.json and warnings.csv.": "A partial scan or access errors mean the inventory is incomplete. See scan_report.json and warnings.csv.",
        "How an AI assistant should use this package": "How an AI assistant should use this package",
        "Use system_profile.json to understand the machine environment; installed_software.csv to identify selected software; volumes.csv for storage; folders.csv and files.csv as a searchable metadata index only. Do not assume the package contains file contents.": "Use system_profile.json to understand the machine environment; installed_software.csv to identify selected software; volumes.csv for storage; folders.csv and files.csv as a searchable metadata index only. Do not assume the package contains file contents.",
    },
}



# Additional message fragments and dynamic README lines.
EXTRA_TRANSLATIONS = {
    "zh": {
        "PC基本情報": "电脑基本信息", "含む": "包含", "除外": "排除",
        "ファイルメタデータ": "文件元数据", "警告": "警告", "除外集計": "排除项统计",
        "以下の内容でAI向けZIPを作成します。": "将按以下内容创建 AI 资料 ZIP。",
        "ZIP内のファイル名・パス・メタデータは閲覧可能です。個人情報が含まれていないことを確認しましたか？": "ZIP 中的文件名、路径和元数据均可被查看。请确认其中不含不应分享的个人信息。",
        "保存先：": "保存位置：", "サイズ：": "大小：", "収録件数：": "收录数量：",
        "少なくとも1つのカテゴリを選択してください。": "请至少选择一个类别。",
        "スキャンを停止しました。": "已停止扫描。",
    },
    "ja": {
        "PC基本情報": "PC基本情報", "含む": "含む", "除外": "除外",
        "ファイルメタデータ": "ファイルメタデータ", "警告": "警告", "除外集計": "除外集計",
        "以下の内容でAI向けZIPを作成します。": "以下の内容でAI向けZIPを作成します。",
        "ZIP内のファイル名・パス・メタデータは閲覧可能です。個人情報が含まれていないことを確認しましたか？": "ZIP内のファイル名・パス・メタデータは閲覧可能です。個人情報が含まれていないことを確認しましたか？",
        "保存先：": "保存先：", "サイズ：": "サイズ：", "収録件数：": "収録件数：",
    },
    "ko": {
        "PC基本情報": "PC 기본 정보", "含む": "포함", "除外": "제외",
        "ファイルメタデータ": "파일 메타데이터", "警告": "경고", "除外集計": "제외 항목 집계",
        "以下の内容でAI向けZIPを作成します。": "다음 내용으로 AI용 ZIP을 만듭니다.",
        "ZIP内のファイル名・パス・メタデータは閲覧可能です。個人情報が含まれていないことを確認しましたか？": "ZIP 안의 파일 이름, 경로 및 메타데이터는 열람할 수 있습니다. 공유해서는 안 될 개인정보가 포함되지 않았는지 확인하세요.",
        "保存先：": "저장 위치:", "サイズ：": "크기:", "収録件数：": "포함 항목 수:",
    },
    "en": {
        "PC基本情報": "PC profile", "含む": "Include", "除外": "Exclude",
        "ファイルメタデータ": "File metadata", "警告": "Warnings", "除外集計": "Exclusion summary",
        "以下の内容でAI向けZIPを作成します。": "The AI context ZIP will be created with the following contents.",
        "ZIP内のファイル名・パス・メタデータは閲覧可能です。個人情報が含まれていないことを確認しましたか？": "File names, paths, and metadata in the ZIP will be visible. Have you checked that it contains no personal information you should not share?",
        "保存先：": "Output folder:", "サイズ：": "Size:", "収録件数：": "Record counts:",
    },
}
for _language, _values in EXTRA_TRANSLATIONS.items():
    TRANSLATIONS[_language].update(_values)



EXTRA_TRANSLATIONS_2 = {
    "zh": {
        "件": "项", "スキップされた項目：": "已跳过项目：",
        "アクセス／メタデータ取得エラー：": "访问／元数据获取错误：",
        "ファイル：": "文件：", "フォルダー：": "文件夹：", "スキャン状態：": "扫描状态：",
        "除外理由の集計を梱包する": "打包排除原因统计", "スキャン警告を梱包する": "打包扫描警告",
        "AI向けZIPを作成しました。": "已创建 AI 资料 ZIP。",
        "収録件数：": "收录数量：",
    },
    "ja": {"件": "件"},
    "ko": {
        "件": "개", "スキップされた項目：": "건너뛴 항목:",
        "アクセス／メタデータ取得エラー：": "접근 / 메타데이터 수집 오류:",
        "ファイル：": "파일:", "フォルダー：": "폴더:", "スキャン状態：": "스캔 상태:",
        "除外理由の集計を梱包する": "제외 사유 집계 패키징", "スキャン警告を梱包する": "스캔 경고 패키징",
        "AI向けZIPを作成しました。": "AI용 ZIP을 만들었습니다.",
        "収録件数：": "포함 항목 수:",
    },
    "en": {
        "件": "items", "スキップされた項目：": "Skipped items:",
        "アクセス／メタデータ取得エラー：": "Access / metadata errors:",
        "ファイル：": "Files:", "フォルダー：": "Folders:", "スキャン状態：": "Scan status:",
        "除外理由の集計を梱包する": "Include exclusion-reason summary", "スキャン警告を梱包する": "Include scan warnings",
        "AI向けZIPを作成しました。": "The AI context ZIP was created.",
        "収録件数：": "Record counts:",
    },
}
for _language, _values in EXTRA_TRANSLATIONS_2.items():
    TRANSLATIONS[_language].update(_values)



EXTRA_TRANSLATIONS_3 = {
    "zh": {
        "フォルダー": "文件夹", "現在：": "当前版本：",
        "除外理由の集計を梱包する": "打包排除原因统计",
        "機微候補として検出されたファイル名が": "检测到疑似敏感文件名，数量为",
    },
    "ja": {
        "フォルダー": "フォルダー", "現在：": "現在：",
        "機微候補として検出されたファイル名が": "機微候補として検出されたファイル名が",
    },
    "ko": {
        "フォルダー": "폴더", "現在：": "현재 버전:",
        "機微候補として検出されたファイル名が": "민감 정보 후보로 감지된 파일 이름이",
    },
    "en": {
        "フォルダー": "Folders", "現在：": "Current:",
        "機微候補として検出されたファイル名が": "Sensitive-candidate file names detected:",
    },
}
for _language, _values in EXTRA_TRANSLATIONS_3.items():
    TRANSLATIONS[_language].update(_values)



EXTRA_TRANSLATIONS_4 = {
    "zh": {
        "スキャンエラー": "扫描错误", "ブラウザー": "浏览器", "サイズ：": "大小：",
        "64-bit/不明": "64 位／未知", "ユーザーがスキャンを停止しました。": "用户已停止扫描。",
    },
    "ja": {
        "スキャンエラー": "スキャンエラー", "ブラウザー": "ブラウザー", "サイズ：": "サイズ：",
        "64-bit/不明": "64-bit／不明", "ユーザーがスキャンを停止しました。": "ユーザーがスキャンを停止しました。",
    },
    "ko": {
        "スキャンエラー": "스캔 오류", "ブラウザー": "브라우저", "サイズ：": "크기:",
        "64-bit/不明": "64비트 / 알 수 없음", "ユーザーがスキャンを停止しました。": "사용자가 스캔을 중지했습니다.",
    },
    "en": {
        "スキャンエラー": "Scan error", "ブラウザー": "Browser", "サイズ：": "Size:",
        "64-bit/不明": "64-bit / unknown", "ユーザーがスキャンを停止しました。": "The user stopped the scan.",
    },
}
for _language, _values in EXTRA_TRANSLATIONS_4.items():
    TRANSLATIONS[_language].update(_values)



FONT_FAMILIES = {
    "zh": "Microsoft YaHei UI",
    "ja": "Yu Gothic UI",
    "ko": "Malgun Gothic",
    "en": "Segoe UI",
}


def ui_font(language: str, size: int, weight: str | None = None):
    """Choose a Windows UI font with native glyph coverage for the selected locale."""
    family = FONT_FAMILIES.get(language, FONT_FAMILIES["en"])
    return (family, size, weight) if weight else (family, size)



EXTRA_TRANSLATIONS_5 = {
    "zh": {"Yes": "是", "No": "否", "completed": "已完成", "partial_errors": "部分完成（有错误）"},
    "ja": {"Yes": "はい", "No": "いいえ", "completed": "完了", "partial_errors": "一部エラーあり"},
    "ko": {"Yes": "예", "No": "아니요", "completed": "완료", "partial_errors": "부분 완료(오류 포함)"},
    "en": {"Yes": "Yes", "No": "No", "completed": "completed", "partial_errors": "partial (with errors)"},
}
for _language, _values in EXTRA_TRANSLATIONS_5.items():
    TRANSLATIONS[_language].update(_values)


def detect_system_language() -> str:
    """Map the Windows/user locale to one of the four supported languages."""
    try:
        value = locale.getlocale()[0] or ""
    except Exception:
        value = ""
    value = value.replace("-", "_").lower()
    if value.startswith("zh") or "chinese" in value:
        return "zh"
    if value.startswith("ja") or "japanese" in value:
        return "ja"
    if value.startswith("ko") or "korean" in value:
        return "ko"
    return "en"


def _settings_path() -> Path:
    root = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(root) / "PC Context Builder" / "settings.json"


def load_language_preference() -> str:
    try:
        data = json.loads(_settings_path().read_text(encoding="utf-8"))
        code = data.get("language")
        if code in LANGUAGE_NAMES:
            return code
    except (OSError, ValueError, TypeError):
        pass
    return detect_system_language()


def save_language_preference(language: str) -> None:
    if language not in LANGUAGE_NAMES:
        raise ValueError("Unsupported language")
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps({"language": language}, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, path)


def _dynamic_translation(text: str, language: str) -> str:
    """Translate frequently changing count/status strings without touching data values."""
    patterns = [
        (
            r"ファイル (?P<files>[\d,]+) 件 / フォルダー (?P<folders>[\d,]+) 件 / 除外 (?P<skipped>[\d,]+) 件 / エラー (?P<errors>[\d,]+) 件",
            {
                "zh": "文件 {files} 个 / 文件夹 {folders} 个 / 已排除 {skipped} 个 / 错误 {errors} 个",
                "ja": "ファイル {files} 件 / フォルダー {folders} 件 / 除外 {skipped} 件 / エラー {errors} 件",
                "ko": "파일 {files}개 / 폴더 {folders}개 / 제외 {skipped}개 / 오류 {errors}개",
                "en": "{files} files / {folders} folders / {skipped} excluded / {errors} errors",
            },
        ),
        (
            r"インストール済みソフトウェア一覧を梱包する（(?P<count>[\d,]+)件）",
            {"zh": "打包已安装软件列表（{count} 项）", "ja": "インストール済みソフトウェア一覧を梱包する（{count}件）", "ko": "설치된 소프트웨어 목록 패키징({count}개)", "en": "Include installed software list ({count} items)"},
        ),
        (
            r"ローカル固定ドライブ一覧を梱包する（(?P<count>[\d,]+)件）",
            {"zh": "打包本地固定驱动器列表（{count} 项）", "ja": "ローカル固定ドライブ一覧を梱包する（{count}件）", "ko": "로컬 고정 드라이브 목록 패키징({count}개)", "en": "Include local fixed-drive list ({count} items)"},
        ),
        (
            r"フォルダー一覧を梱包（(?P<count>[\d,]+)件）",
            {"zh": "打包文件夹列表（{count} 项）", "ja": "フォルダー一覧を梱包（{count}件）", "ko": "폴더 목록 패키징({count}개)", "en": "Include folder list ({count} items)"},
        ),
        (
            r"ファイル名・パス等のメタデータを梱包（(?P<count>[\d,]+)件）",
            {"zh": "打包文件名、路径等元数据（{count} 项）", "ja": "ファイル名・パス等のメタデータを梱包（{count}件）", "ko": "파일 이름, 경로 등 메타데이터 패키징({count}개)", "en": "Include file-name, path, and other metadata ({count} items)"},
        ),
        (
            r"フォルダー一覧（(?P<count>[\d,]+) 件）",
            {"zh": "文件夹列表（{count} 项）", "ja": "フォルダー一覧（{count} 件）", "ko": "폴더 목록({count}개)", "en": "Folder list ({count} items)"},
        ),
        (
            r"検索結果 (?P<found>[\d,]+) 件 / 全アプリ (?P<all>[\d,]+) 件 / 選択 (?P<selected>[\d,]+) 件 / ページ (?P<page>\d+)/(?P<pages>\d+)（1ページ (?P<size>[\d,]+) 件）",
            {
                "zh": "搜索结果 {found} 项 / 全部应用 {all} 项 / 已选择 {selected} 项 / 第 {page}/{pages} 页（每页 {size} 项）",
                "ja": "検索結果 {found} 件 / 全アプリ {all} 件 / 選択 {selected} 件 / ページ {page}/{pages}（1ページ {size} 件）",
                "ko": "검색 결과 {found}개 / 전체 앱 {all}개 / 선택 {selected}개 / {page}/{pages}페이지(페이지당 {size}개)",
                "en": "{found} results / {all} apps / {selected} selected / page {page}/{pages} ({size} per page)",
            },
        ),
        (
            r"検索結果 (?P<total>[\d,]+) / 選択 (?P<selected>[\d,]+) / (?P<page>\d+)/(?P<pages>\d+)",
            {
                "zh": "搜索结果 {total} 项 / 已选择 {selected} 项 / 第 {page}/{pages} 页",
                "ja": "検索結果 {total} / 選択 {selected} / {page}/{pages}",
                "ko": "검색 결과 {total}개 / 선택 {selected}개 / {page}/{pages}페이지",
                "en": "{total} results / {selected} selected / page {page}/{pages}",
            },
        ),
        (
            r"表示 (?P<shown>[\d,]+) 件 / 全体 (?P<total>[\d,]+) 件 / 現在の選択 (?P<selected>[\d,]+) 件。検索・ページ移動で全件を確認できます。1ページ (?P<size>[\d,]+) 件です。",
            {
                "zh": "当前显示 {shown} 项 / 总计 {total} 项 / 当前已选择 {selected} 项。可通过搜索和翻页检查全部项目。每页 {size} 项。",
                "ja": "表示 {shown} 件 / 全体 {total} 件 / 現在の選択 {selected} 件。検索・ページ移動で全件を確認できます。1ページ {size} 件です。",
                "ko": "표시 {shown}개 / 전체 {total}개 / 현재 선택 {selected}개. 검색 및 페이지 이동으로 전체 항목을 확인할 수 있습니다. 페이지당 {size}개입니다.",
                "en": "Showing {shown} / {total} total / {selected} selected. Use search and paging to review all items. {size} items per page.",
            },
        ),
        (
            r"検索結果 (?P<total>[\d,]+) 件 / 選択 (?P<selected>[\d,]+) 件 / (?P<page>\d+)/(?P<pages>\d+)",
            {
                "zh": "搜索结果 {total} 项 / 已选择 {selected} 项 / 第 {page}/{pages} 页",
                "ja": "検索結果 {total} 件 / 選択 {selected} 件 / {page}/{pages}",
                "ko": "검색 결과 {total}개 / 선택 {selected}개 / {page}/{pages}페이지",
                "en": "{total} results / {selected} selected / page {page}/{pages}",
            },
        ),
        (
            r"ファイル構造を調査しています（選択ドライブ (?P<count>\d+) 個）\.\.\.",
            {"zh": "正在扫描文件结构（已选驱动器 {count} 个）……", "ja": "ファイル構造を調査しています（選択ドライブ {count} 個）...", "ko": "파일 구조를 검사하는 중(선택한 드라이브 {count}개)...", "en": "Scanning file structure ({count} selected drives)..."},
        ),
        (
            r"ファイル (?P<files>[\d,]+) / フォルダー (?P<folders>[\d,]+) / 除外 (?P<skipped>[\d,]+) / エラー (?P<errors>[\d,]+) — (?P<current>.*)",
            {
                "zh": "文件 {files} / 文件夹 {folders} / 已排除 {skipped} / 错误 {errors} — {current}",
                "ja": "ファイル {files} / フォルダー {folders} / 除外 {skipped} / エラー {errors} — {current}",
                "ko": "파일 {files} / 폴더 {folders} / 제외 {skipped} / 오류 {errors} — {current}",
                "en": "{files} files / {folders} folders / {skipped} excluded / {errors} errors — {current}",
            },
        ),
        (
            r"ファイル (?P<files>[\d,]+) 件 / フォルダー (?P<folders>[\d,]+) 件 / 状態 (?P<status>.*)",
            {
                "zh": "文件 {files} 个 / 文件夹 {folders} 个 / 状态 {status}",
                "ja": "ファイル {files} 件 / フォルダー {folders} 件 / 状態 {status}",
                "ko": "파일 {files}개 / 폴더 {folders}개 / 상태 {status}",
                "en": "{files} files / {folders} folders / status {status}",
            },
        ),
        (
            r"ファイル (?P<files>[\d,]+) 件 / フォルダー (?P<folders>[\d,]+) 件 / 除外 (?P<skipped>[\d,]+) 件 / エラー (?P<errors>[\d,]+) 件",
            {
                "zh": "文件 {files} 个 / 文件夹 {folders} 个 / 已排除 {skipped} 个 / 错误 {errors} 个",
                "ja": "ファイル {files} 件 / フォルダー {folders} 件 / 除外 {skipped} 件 / エラー {errors} 件",
                "ko": "파일 {files}개 / 폴더 {folders}개 / 제외 {skipped}개 / 오류 {errors}개",
                "en": "{files} files / {folders} folders / {skipped} excluded / {errors} errors",
            },
        ),

        (
            r"除外理由の集計を梱包する（検出 (?P<count>[\d,]+) 件）",
            {"zh": "打包排除原因统计（检测到 {count} 项）", "ja": "除外理由の集計を梱包する（検出 {count} 件）", "ko": "제외 사유 집계 패키징(감지 {count}개)", "en": "Include exclusion-reason summary ({count} detected)"},
        ),
        (
            r"スキャン警告を梱包する（(?P<count>[\d,]+) 件）",
            {"zh": "打包扫描警告（{count} 项）", "ja": "スキャン警告を梱包する（{count} 件）", "ko": "스캔 경고 패키징({count}개)", "en": "Include scan warnings ({count} items)"},
        ),
        (
            r"PC profile was not selected for inclusion\.",
            {"zh": "未选择包含电脑基本信息。", "ja": "PC基本情報は収録対象に選択されていません。", "ko": "PC 프로필은 포함하도록 선택되지 않았습니다.", "en": "PC profile was not selected for inclusion."},
        ),

        (
            r"Schema version: (?P<version>.*)",
            {"zh": "架构版本：{version}", "ja": "スキーマバージョン：{version}", "ko": "스키마 버전: {version}", "en": "Schema version: {version}"},
        ),
        (
            r"Scan time: (?P<time>.*)",
            {"zh": "扫描时间：{time}", "ja": "スキャン時刻：{time}", "ko": "스캔 시간: {time}", "en": "Scan time: {time}"},
        ),
        (
            r"OS: (?P<value>.*)",
            {"zh": "操作系统：{value}", "ja": "OS：{value}", "ko": "운영 체제: {value}", "en": "OS: {value}"},
        ),
        (
            r"Architecture: (?P<value>.*)",
            {"zh": "架构：{value}", "ja": "アーキテクチャ：{value}", "ko": "아키텍처: {value}", "en": "Architecture: {value}"},
        ),
        (
            r"Manufacturer / Model: (?P<value>.*)",
            {"zh": "制造商／型号：{value}", "ja": "メーカー／モデル：{value}", "ko": "제조사 / 모델: {value}", "en": "Manufacturer / Model: {value}"},
        ),
        (
            r"Motherboard: (?P<value>.*)",
            {"zh": "主板：{value}", "ja": "マザーボード：{value}", "ko": "마더보드: {value}", "en": "Motherboard: {value}"},
        ),
        (
            r"CPU: (?P<value>.*)",
            {"zh": "CPU：{value}", "ja": "CPU：{value}", "ko": "CPU: {value}", "en": "CPU: {value}"},
        ),
        (
            r"Physical memory: (?P<value>.*)",
            {"zh": "物理内存：{value}", "ja": "物理メモリ：{value}", "ko": "물리 메모리: {value}", "en": "Physical memory: {value}"},
        ),
        (
            r"GPU: (?P<value>.*)",
            {"zh": "GPU：{value}", "ja": "GPU：{value}", "ko": "GPU: {value}", "en": "GPU: {value}"},
        ),
        (
            r"Display: (?P<value>.*)",
            {"zh": "显示器：{value}", "ja": "ディスプレイ：{value}", "ko": "디스플레이: {value}", "en": "Display: {value}"},
        ),
        (
            r"(?P<label>PC profile|Installed software|Storage|Folder index|File metadata index|Scan warnings|Security/exclusion summary): (?P<state>included|not included) \((?P<count>[\d,]+) records\)",
            {
                "zh": "{label}：{state}（{count} 条记录）",
                "ja": "{label}：{state}（{count} 件）",
                "ko": "{label}: {state}({count}개 레코드)",
                "en": "{label}: {state} ({count} records)",
            },
        ),
        (
            r"警告：機微候補として検出されたファイル名が (?P<count>[\d,]+) 件含まれます。必要なものだけを残してください。",
            {
                "zh": "警告：包含 {count} 个疑似敏感文件名。请仅保留确实需要的项目。",
                "ja": "警告：機微候補として検出されたファイル名が {count} 件含まれます。必要なものだけを残してください。",
                "ko": "주의: 민감 정보 후보 파일 이름 {count}개가 포함됩니다. 필요한 항목만 남겨 주세요.",
                "en": "Warning: {count} sensitive-candidate file names are included. Keep only what you need.",
            },
        ),
    ]
    for pattern, templates in patterns:
        match = re.fullmatch(pattern, text)
        if match:
            values = match.groupdict()
            table = TRANSLATIONS.get(language, {})
            for field in ("label", "state"):
                if values.get(field):
                    values[field] = table.get(values[field], values[field])
            return templates[language].format(**values)
    return text


def tr(text, language: str | None = None) -> str:
    if not isinstance(text, str):
        return text
    language = language or detect_system_language()
    if language == "ja":
        # Japanese is the original UI language, but README source copy is English.
        table = TRANSLATIONS["ja"]
    else:
        table = TRANSLATIONS.get(language, TRANSLATIONS["en"])
    for prefix in ("### ", "## ", "# ", "- "):
        if text.startswith(prefix):
            body = text[len(prefix):]
            translated_body = table.get(body)
            if translated_body is None:
                translated_body = _dynamic_translation(body, language)
            return prefix + translated_body
    if text in table:
        return table[text]
    return _dynamic_translation(text, language)


def translate_widget_tree(root, language: str) -> None:
    """Translate visible widget labels, notebook tabs, and Treeview headings."""
    try:
        if isinstance(root, ttk.Notebook):
            for tab_id in root.tabs():
                old = root.tab(tab_id, "text")
                root.tab(tab_id, text=tr(old, language))
        if isinstance(root, ttk.Treeview):
            for column in root["columns"]:
                old = root.heading(column, "text")
                if old:
                    root.heading(column, text=tr(old, language))
        try:
            old_text = root.cget("text")
            if old_text:
                root.configure(text=tr(old_text, language))
        except Exception:
            pass
    except Exception:
        pass
    try:
        children = root.winfo_children()
    except Exception:
        children = []
    for child in children:
        translate_widget_tree(child, language)
