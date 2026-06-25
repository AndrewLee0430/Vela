// utils/i18n-faq.ts — FAQ translations for 16 languages
import type { LangCode } from './i18n';

export interface FAQItemI18n { q: string; a: string; }
export interface FAQSectionI18n { title: string; items: FAQItemI18n[]; }

export const faqSectionsI18n: Record<LangCode, FAQSectionI18n[]> = {
  en: [
    {
      title: 'About Vela',
      items: [
        { q: 'What is Vela?', a: "Vela is a clinical knowledge engine for healthcare professionals. It searches PubMed's 40 million+ articles, checks drug interactions against official FDA data, and explains medical reports using LOINC, RxNorm, and MedlinePlus standards \u2014 all in 16 languages." },
        { q: "Why are Vela's answers cited with sources?", a: 'Every answer in Vela is traced back to PubMed, FDA, or LOINC. You can verify any claim by clicking through to the original source. We believe medical information should always be traceable and independently verifiable.' },
        { q: 'What data sources does Vela use?', a: 'Vela integrates three authoritative medical databases: PubMed (40M+ peer-reviewed articles from the National Library of Medicine), FDA drug labels (OpenFDA) (official drug label and interaction data), and LOINC/MedlinePlus (standardized lab test definitions and health information from NIH).' },
        { q: 'What languages does Vela support?', a: 'Vela supports 16 languages: English, Traditional Chinese, Simplified Chinese, Japanese, Korean, Thai, Spanish, French, German, Portuguese, Indonesian, Vietnamese, Arabic, Hindi, Bengali, and Hebrew. You can ask questions in any of these languages and receive answers in the same language.' },
      ],
    },
    {
      title: 'Features',
      items: [
        { q: 'What is Research?', a: 'Research lets you ask clinical questions in natural language. Vela searches PubMed, retrieves relevant peer-reviewed articles, and synthesizes an evidence-graded answer with full citations. Each source is linked so you can read the original paper.' },
        { q: 'What is Verify?', a: 'Verify checks drug interactions using official FDA drug labels (OpenFDA) data. Enter two or more drug names and Vela returns the interaction severity level, clinical effects, and management recommendations \u2014 all sourced from FDA-approved drug labels.' },
        { q: 'What is Explain?', a: "Explain helps you understand medical reports. Paste your lab results or upload a report (PDF or image), and Vela breaks down each value in plain language \u2014 what it measures, whether it's normal, and what it might mean. Sources include LOINC standards, RxNorm drug data, and MedlinePlus health information." },
        { q: 'What does evidence strength mean?', a: 'Vela grades each section of a Research answer by the strength of the supporting evidence. Strong evidence (green) comes from systematic reviews or large clinical trials. Moderate evidence (yellow) comes from smaller studies. Limited evidence (red) means the supporting research is preliminary. This helps you quickly assess how reliable each part of the answer is.' },
      ],
    },
    {
      title: 'Privacy & Safety',
      items: [
        { q: 'Is Vela a medical device?', a: 'No. Vela is a research and reference tool. It does not diagnose, treat, or provide medical advice. All outputs include a disclaimer reminding users to consult a qualified healthcare professional for clinical decisions.' },
        { q: 'Does Vela protect my data?', a: 'Vela actively detects and blocks personal health identifiers (PHI) before processing any query. Chat history is automatically deleted after 180 days. Vela runs on secure, encrypted infrastructure. For full details, see our Privacy Policy.' },
        { q: 'Who built Vela?', a: 'Vela is built by an-tho (an-tho.com), a company focused on building evidence-driven decision support systems. Vela is the first product in this mission.' },
      ],
    },
    {
      title: 'Pricing',
      items: [
        { q: 'How much does Vela cost?', a: 'Vela offers a free plan with limited daily queries across all three features. The Pro plan is $9.99/month or $89.99/year (save 25%), which includes unlimited queries, PDF/image upload for Explain, and PDF export.' },
        { q: "What's included in the free plan?", a: 'The free plan includes access to all three features \u2014 Research, Verify, and Explain \u2014 with a limited number of queries per day. No credit card required.' },
        { q: "What's included in Pro?", a: 'Pro includes unlimited queries across all features, PDF and image upload for Explain, PDF export of results, and priority access to new features.' },
        { q: 'Can I cancel anytime?', a: 'Yes. You can cancel your Pro subscription at any time from your account settings. Your access continues until the end of the current billing period. No cancellation fees.' },
      ],
    },
  ],
  'zh-TW': [
    {
      title: '關於 Vela',
      items: [
        { q: '什麼是 Vela？', a: 'Vela 是為醫療專業人員打造的臨床知識引擎。它搜尋 PubMed 超過 4000 萬篇文章，根據 FDA 官方資料檢查藥物交互作用，並使用 LOINC、RxNorm 和 MedlinePlus 標準解讀醫療報告——支援 16 種語言。' },
        { q: '為什麼 Vela 的回答都附有來源引用？', a: 'Vela 的每個回答都可追溯至 PubMed、FDA 或 LOINC。您可以點擊原始來源驗證任何說法。我們相信醫療資訊應始終可追溯且可獨立驗證。' },
        { q: 'Vela 使用哪些資料來源？', a: 'Vela 整合三個權威醫學資料庫：PubMed（美國國家醫學圖書館 4000 萬+篇同儕審查文章）、FDA drug labels (OpenFDA)（官方藥物標示與交互作用資料）、以及 LOINC/MedlinePlus（NIH 標準化檢驗定義與健康資訊）。' },
        { q: 'Vela 支援哪些語言？', a: 'Vela 支援 16 種語言：英語、繁體中文、簡體中文、日語、韓語、泰語、西班牙語、法語、德語、葡萄牙語、印尼語、越南語、阿拉伯語、印地語、孟加拉語和希伯來語。您可以用任何一種語言提問，並以相同語言收到回答。' },
      ],
    },
    {
      title: '功能',
      items: [
        { q: '什麼是研究（Research）？', a: '研究功能讓您以自然語言提出臨床問題。Vela 搜尋 PubMed，檢索相關的同儕審查文章，並綜合出帶有完整引用的證據分級回答。每個來源都附有連結，方便您閱讀原始論文。' },
        { q: '什麼是驗證（Verify）？', a: '驗證功能使用 FDA drug labels (OpenFDA) 官方資料檢查藥物交互作用。輸入兩種或更多藥物名稱，Vela 會回傳交互作用嚴重程度、臨床影響和處理建議——全部來自 FDA 核准的藥物標示。' },
        { q: '什麼是解讀（Explain）？', a: '解讀功能幫助您理解醫療報告。貼上您的檢驗結果或上傳報告（PDF 或圖片），Vela 會以淺顯語言逐項說明每個數值——它測量什麼、是否正常、可能代表什麼。來源包括 LOINC 標準、RxNorm 藥物資料和 MedlinePlus 健康資訊。' },
        { q: '證據強度是什麼意思？', a: 'Vela 根據支持證據的強度對研究回答的每個部分進行分級。強力證據（綠色）來自系統性回顧或大型臨床試驗。中等證據（黃色）來自較小型研究。有限證據（紅色）表示支持研究尚屬初步。這有助於您快速評估回答各部分的可靠性。' },
      ],
    },
    {
      title: '隱私與安全',
      items: [
        { q: 'Vela 是醫療器材嗎？', a: '不是。Vela 是研究與參考工具，不進行診斷、治療或提供醫療建議。所有輸出都包含免責聲明，提醒使用者就臨床決策諮詢合格的醫療專業人員。' },
        { q: 'Vela 會保護我的資料嗎？', a: 'Vela 在處理任何查詢前會主動偵測並阻擋個人健康識別資訊（PHI）。聊天記錄在 180 天後自動刪除。Vela 運行在安全、加密的基礎設施上。詳細資訊請參閱我們的隱私權政策。' },
        { q: '誰建立了 Vela？', a: 'Vela 由 an-tho（an-tho.com）建立，這是一家專注於建構證據驅動決策支援系統的公司。Vela 是這項使命的第一個產品。' },
      ],
    },
    {
      title: '定價',
      items: [
        { q: 'Vela 的費用是多少？', a: 'Vela 提供免費方案，三項功能皆有每日有限查詢次數。Pro 方案為每月 $9.99 或每年 $89.99（省 25%），包含無限查詢、解讀的 PDF/圖片上傳和 PDF 匯出。' },
        { q: '免費方案包含什麼？', a: '免費方案可使用全部三項功能——研究、驗證和解讀——每日查詢次數有限。無需信用卡。' },
        { q: 'Pro 包含什麼？', a: 'Pro 包含所有功能的無限查詢、解讀的 PDF 和圖片上傳、結果的 PDF 匯出，以及新功能的優先使用權。' },
        { q: '可以隨時取消嗎？', a: '可以。您可以隨時從帳戶設定中取消 Pro 訂閱。您的存取權限將持續到當前計費週期結束。無取消費用。' },
      ],
    },
  ],
  'zh-CN': [
    {
      title: '关于 Vela',
      items: [
        { q: '什么是 Vela？', a: 'Vela 是为医疗专业人员打造的临床知识引擎。它搜索 PubMed 超过 4000 万篇文章，根据 FDA 官方数据检查药物相互作用，并使用 LOINC、RxNorm 和 MedlinePlus 标准解读医疗报告——支持 16 种语言。' },
        { q: '为什么 Vela 的回答都附有来源引用？', a: 'Vela 的每个回答都可追溯至 PubMed、FDA 或 LOINC。您可以点击原始来源验证任何说法。我们相信医疗信息应始终可追溯且可独立验证。' },
        { q: 'Vela 使用哪些数据来源？', a: 'Vela 整合三个权威医学数据库：PubMed（美国国家医学图书馆 4000 万+篇同行评审文章）、FDA drug labels (OpenFDA)（官方药物标签与相互作用数据）、以及 LOINC/MedlinePlus（NIH 标准化检验定义与健康信息）。' },
        { q: 'Vela 支持哪些语言？', a: 'Vela 支持 16 种语言：英语、繁体中文、简体中文、日语、韩语、泰语、西班牙语、法语、德语、葡萄牙语、印尼语、越南语、阿拉伯语、印地语、孟加拉语和希伯来语。您可以用任何一种语言提问，并以相同语言收到回答。' },
      ],
    },
    {
      title: '功能',
      items: [
        { q: '什么是研究（Research）？', a: '研究功能让您以自然语言提出临床问题。Vela 搜索 PubMed，检索相关的同行评审文章，并综合出带有完整引用的证据分级回答。每个来源都附有链接，方便您阅读原始论文。' },
        { q: '什么是验证（Verify）？', a: '验证功能使用 FDA drug labels (OpenFDA) 官方数据检查药物相互作用。输入两种或更多药物名称，Vela 会返回相互作用严重程度、临床影响和处理建议——全部来自 FDA 批准的药物标签。' },
        { q: '什么是解读（Explain）？', a: '解读功能帮助您理解医疗报告。粘贴您的检验结果或上传报告（PDF 或图片），Vela 会以通俗语言逐项说明每个数值——它测量什么、是否正常、可能代表什么。来源包括 LOINC 标准、RxNorm 药物数据和 MedlinePlus 健康信息。' },
        { q: '证据强度是什么意思？', a: 'Vela 根据支持证据的强度对研究回答的每个部分进行分级。强力证据（绿色）来自系统性综述或大型临床试验。中等证据（黄色）来自较小型研究。有限证据（红色）表示支持研究尚属初步。这有助于您快速评估回答各部分的可靠性。' },
      ],
    },
    {
      title: '隐私与安全',
      items: [
        { q: 'Vela 是医疗器械吗？', a: '不是。Vela 是研究与参考工具，不进行诊断、治疗或提供医疗建议。所有输出都包含免责声明，提醒用户就临床决策咨询合格的医疗专业人员。' },
        { q: 'Vela 会保护我的数据吗？', a: 'Vela 在处理任何查询前会主动检测并阻止个人健康标识信息（PHI）。聊天记录在 180 天后自动删除。Vela 运行在安全、加密的基础设施上。详细信息请参阅我们的隐私政策。' },
        { q: '谁建立了 Vela？', a: 'Vela 由 an-tho（an-tho.com）建立，这是一家专注于构建证据驱动决策支持系统的公司。Vela 是这项使命的第一个产品。' },
      ],
    },
    {
      title: '定价',
      items: [
        { q: 'Vela 的费用是多少？', a: 'Vela 提供免费方案，三项功能皆有每日有限查询次数。Pro 方案为每月 $9.99 或每年 $89.99（省 25%），包含无限查询、解读的 PDF/图片上传和 PDF 导出。' },
        { q: '免费方案包含什么？', a: '免费方案可使用全部三项功能——研究、验证和解读——每日查询次数有限。无需信用卡。' },
        { q: 'Pro 包含什么？', a: 'Pro 包含所有功能的无限查询、解读的 PDF 和图片上传、结果的 PDF 导出，以及新功能的优先使用权。' },
        { q: '可以随时取消吗？', a: '可以。您可以随时从账户设置中取消 Pro 订阅。您的访问权限将持续到当前计费周期结束。无取消费用。' },
      ],
    },
  ],
  ja: [
    { title: 'Velaについて', items: [
      { q: 'Velaとは何ですか？', a: 'Velaは医療専門家向けの臨床知識エンジンです。PubMedの4000万以上の論文を検索し、FDA公式データで薬物相互作用を確認し、LOINC、RxNorm、MedlinePlus標準を使用して医療レポートを解説します——16言語に対応。' },
      { q: 'なぜVelaの回答にはソースが引用されているのですか？', a: 'Velaのすべての回答はPubMed、FDA、またはLOINCに遡ることができます。元のソースをクリックして任意の主張を確認できます。医療情報は常に追跡可能で独立して検証可能であるべきだと考えています。' },
      { q: 'Velaはどのデータソースを使用していますか？', a: 'Velaは3つの権威ある医学データベースを統合しています：PubMed（米国国立医学図書館の4000万以上の査読済み論文）、FDA drug labels (OpenFDA)（公式薬物ラベルと相互作用データ）、LOINC/MedlinePlus（NIHの標準化された検査定義と健康情報）。' },
      { q: 'Velaはどの言語をサポートしていますか？', a: 'Velaは16言語をサポートしています：英語、繁体字中国語、簡体字中国語、日本語、韓国語、タイ語、スペイン語、フランス語、ドイツ語、ポルトガル語、インドネシア語、ベトナム語、アラビア語、ヒンディー語、ベンガル語、ヘブライ語。これらの言語で質問し、同じ言語で回答を受け取ることができます。' },
    ]},
    { title: '機能', items: [
      { q: 'リサーチとは？', a: 'リサーチは自然言語で臨床的な質問ができる機能です。VelaはPubMedを検索し、関連する査読済み論文を取得し、完全な引用付きのエビデンスグレード付き回答を合成します。' },
      { q: '検証とは？', a: '検証はFDA drug labels (OpenFDA)の公式データを使用して薬物相互作用を確認します。2つ以上の薬物名を入力すると、Velaは相互作用の重症度、臨床効果、管理推奨事項を返します。' },
      { q: '解説とは？', a: '解説は医療レポートの理解を助けます。検査結果を貼り付けるか、レポート（PDFまたは画像）をアップロードすると、Velaが各値を平易な言葉で解説します。' },
      { q: 'エビデンス強度とは？', a: 'Velaはリサーチ回答の各セクションを支持するエビデンスの強さで評価します。強いエビデンス（緑）はシステマティックレビューや大規模臨床試験から、中程度（黄）は小規模研究から、限定的（赤）は予備的研究を意味します。' },
    ]},
    { title: 'プライバシーと安全性', items: [
      { q: 'Velaは医療機器ですか？', a: 'いいえ。Velaは研究・参照ツールです。診断、治療、医療アドバイスは行いません。すべての出力に免責事項が含まれています。' },
      { q: 'Velaは私のデータを保護しますか？', a: 'Velaはクエリを処理する前に個人健康識別情報（PHI）を積極的に検出・ブロックします。チャット履歴は180日後に自動削除されます。詳細はプライバシーポリシーをご覧ください。' },
      { q: 'Velaは誰が作りましたか？', a: 'Velaはan-tho（an-tho.com）が構築しました。エビデンスに基づく意思決定支援システムの構築に注力する企業です。' },
    ]},
    { title: '料金', items: [
      { q: 'Velaの料金は？', a: 'Velaは全3機能で毎日限定クエリの無料プランを提供しています。Proプランは月額$9.99または年額$89.99（25%お得）で、無制限クエリ、PDF/画像アップロード、PDFエクスポートが含まれます。' },
      { q: '無料プランに含まれるものは？', a: '無料プランでは全3機能（リサーチ、検証、解説）に1日限定回数でアクセスできます。クレジットカード不要。' },
      { q: 'Proに含まれるものは？', a: 'Proには全機能の無制限クエリ、解説のPDF・画像アップロード、結果のPDFエクスポート、新機能への優先アクセスが含まれます。' },
      { q: 'いつでもキャンセルできますか？', a: 'はい。アカウント設定からいつでもProサブスクリプションをキャンセルできます。現在の請求期間終了までアクセスは続きます。キャンセル料はかかりません。' },
    ]},
  ],
  ko: [
    { title: 'Vela 소개', items: [
      { q: 'Vela란 무엇인가요?', a: 'Vela는 의료 전문가를 위한 임상 지식 엔진입니다. PubMed 4000만+ 논문을 검색하고, FDA 공식 데이터로 약물 상호작용을 확인하며, LOINC, RxNorm, MedlinePlus 표준을 사용하여 의료 보고서를 설명합니다 — 16개 언어를 지원합니다.' },
      { q: 'Vela의 답변에 출처가 인용되는 이유는?', a: 'Vela의 모든 답변은 PubMed, FDA 또는 LOINC로 추적할 수 있습니다. 원본 출처를 클릭하여 모든 주장을 확인할 수 있습니다.' },
      { q: 'Vela는 어떤 데이터 소스를 사용하나요?', a: 'Vela는 세 가지 권위 있는 의학 데이터베이스를 통합합니다: PubMed, FDA drug labels (OpenFDA), LOINC/MedlinePlus.' },
      { q: 'Vela는 어떤 언어를 지원하나요?', a: 'Vela는 16개 언어를 지원합니다: 영어, 번체 중국어, 간체 중국어, 일본어, 한국어, 태국어, 스페인어, 프랑스어, 독일어, 포르투갈어, 인도네시아어, 베트남어, 아랍어, 힌디어, 벵골어, 히브리어.' },
    ]},
    { title: '기능', items: [
      { q: '리서치란?', a: '리서치는 자연어로 임상 질문을 할 수 있는 기능입니다. Vela가 PubMed를 검색하여 관련 논문을 찾고 근거 등급이 매겨진 답변을 종합합니다.' },
      { q: '검증이란?', a: '검증은 FDA drug labels (OpenFDA) 공식 데이터를 사용하여 약물 상호작용을 확인합니다. 두 가지 이상의 약물명을 입력하면 상호작용 심각도, 임상 효과, 관리 권장 사항을 반환합니다.' },
      { q: '설명이란?', a: '설명은 의료 보고서를 이해하도록 도와줍니다. 검사 결과를 붙여넣거나 보고서를 업로드하면 Vela가 각 수치를 쉬운 말로 설명합니다.' },
      { q: '근거 강도란?', a: 'Vela는 리서치 답변의 각 섹션을 지원 증거의 강도에 따라 등급을 매깁니다. 강한 증거(녹색), 보통(노란색), 제한적(빨간색)으로 나뉩니다.' },
    ]},
    { title: '개인정보 및 안전', items: [
      { q: 'Vela는 의료 기기인가요?', a: '아닙니다. Vela는 연구 및 참조 도구입니다. 진단, 치료 또는 의료 조언을 제공하지 않습니다.' },
      { q: 'Vela는 내 데이터를 보호하나요?', a: 'Vela는 쿼리를 처리하기 전에 개인 건강 식별 정보(PHI)를 적극적으로 감지하고 차단합니다. 채팅 기록은 180일 후 자동 삭제됩니다.' },
      { q: 'Vela는 누가 만들었나요?', a: 'Vela는 증거 기반 의사결정 지원 시스템 구축에 주력하는 기업인 an-tho(an-tho.com)가 만들었습니다.' },
    ]},
    { title: '요금제', items: [
      { q: 'Vela 비용은 얼마인가요?', a: 'Vela는 세 가지 기능 모두에서 일일 제한 쿼리가 있는 무료 플랜을 제공합니다. Pro 플랜은 월 $9.99 또는 연 $89.99(25% 절약)입니다.' },
      { q: '무료 플랜에 포함된 것은?', a: '무료 플랜은 리서치, 검증, 설명 세 기능 모두에 일일 제한된 쿼리로 액세스할 수 있습니다. 신용카드 불필요.' },
      { q: 'Pro에 포함된 것은?', a: 'Pro에는 모든 기능의 무제한 쿼리, PDF 및 이미지 업로드, PDF 내보내기, 새 기능 우선 액세스가 포함됩니다.' },
      { q: '언제든지 취소할 수 있나요?', a: '네. 계정 설정에서 언제든지 Pro 구독을 취소할 수 있습니다. 현재 청구 기간 종료까지 액세스가 유지됩니다.' },
    ]},
  ],
  es: [
    { title: 'Acerca de Vela', items: [
      { q: '¿Qué es Vela?', a: 'Vela es un motor de conocimiento clínico para profesionales de la salud. Busca en más de 40 millones de artículos de PubMed, verifica interacciones medicamentosas con datos oficiales de la FDA y explica informes médicos usando estándares LOINC, RxNorm y MedlinePlus — en 16 idiomas.' },
      { q: '¿Por qué las respuestas de Vela incluyen fuentes?', a: 'Cada respuesta en Vela es rastreable hasta PubMed, FDA o LOINC. Puede verificar cualquier afirmación haciendo clic en la fuente original.' },
      { q: '¿Qué fuentes de datos usa Vela?', a: 'Vela integra tres bases de datos médicas autorizadas: PubMed, FDA drug labels (OpenFDA) y LOINC/MedlinePlus.' },
      { q: '¿Qué idiomas soporta Vela?', a: 'Vela soporta 16 idiomas: inglés, chino tradicional, chino simplificado, japonés, coreano, tailandés, español, francés, alemán, portugués, indonesio, vietnamita, árabe, hindi, bengalí y hebreo.' },
    ]},
    { title: 'Funciones', items: [
      { q: '¿Qué es Investigar?', a: 'Investigar le permite hacer preguntas clínicas en lenguaje natural. Vela busca en PubMed y sintetiza una respuesta con grado de evidencia y citas completas.' },
      { q: '¿Qué es Verificar?', a: 'Verificar comprueba interacciones medicamentosas usando datos oficiales de FDA drug labels (OpenFDA).' },
      { q: '¿Qué es Explicar?', a: 'Explicar le ayuda a entender informes médicos. Pegue sus resultados de laboratorio o suba un informe y Vela desglosa cada valor en lenguaje sencillo.' },
      { q: '¿Qué significa la fuerza de la evidencia?', a: 'Vela califica cada sección por la fuerza de la evidencia. Evidencia fuerte (verde), moderada (amarillo) y limitada (rojo).' },
    ]},
    { title: 'Privacidad y seguridad', items: [
      { q: '¿Es Vela un dispositivo médico?', a: 'No. Vela es una herramienta de investigación y referencia. No diagnostica, trata ni proporciona asesoramiento médico.' },
      { q: '¿Vela protege mis datos?', a: 'Vela detecta y bloquea activamente identificadores de salud personal (PHI) antes de procesar cualquier consulta. El historial se elimina automáticamente después de 180 días.' },
      { q: '¿Quién creó Vela?', a: 'Vela fue creada por an-tho (an-tho.com), una empresa enfocada en sistemas de apoyo a decisiones basados en evidencia.' },
    ]},
    { title: 'Precios', items: [
      { q: '¿Cuánto cuesta Vela?', a: 'Vela ofrece un plan gratuito con consultas diarias limitadas. El plan Pro es $9.99/mes o $89.99/año (ahorre 25%).' },
      { q: '¿Qué incluye el plan gratuito?', a: 'El plan gratuito incluye acceso a las tres funciones con un número limitado de consultas por día. Sin tarjeta de crédito.' },
      { q: '¿Qué incluye Pro?', a: 'Pro incluye consultas ilimitadas, carga de PDF e imágenes, exportación PDF y acceso prioritario a nuevas funciones.' },
      { q: '¿Puedo cancelar en cualquier momento?', a: 'Sí. Puede cancelar desde la configuración de su cuenta en cualquier momento. Sin cargos por cancelación.' },
    ]},
  ],
  fr: [
    { title: 'À propos de Vela', items: [
      { q: 'Qu\u2019est-ce que Vela ?', a: 'Vela est un moteur de connaissances cliniques pour les professionnels de santé. Il recherche dans plus de 40 millions d\u2019articles PubMed, vérifie les interactions médicamenteuses avec les données officielles de la FDA et explique les rapports médicaux — en 16 langues.' },
      { q: 'Pourquoi les réponses de Vela sont-elles citées ?', a: 'Chaque réponse est traçable jusqu\u2019à PubMed, FDA ou LOINC. Vous pouvez vérifier toute affirmation en cliquant sur la source originale.' },
      { q: 'Quelles sources de données Vela utilise-t-il ?', a: 'Vela intègre trois bases de données médicales faisant autorité : PubMed, FDA drug labels (OpenFDA) et LOINC/MedlinePlus.' },
      { q: 'Quelles langues Vela prend-il en charge ?', a: 'Vela prend en charge 16 langues : anglais, chinois traditionnel, chinois simplifié, japonais, coréen, thaï, espagnol, français, allemand, portugais, indonésien, vietnamien, arabe, hindi, bengali et hébreu.' },
    ]},
    { title: 'Fonctionnalités', items: [
      { q: 'Qu\u2019est-ce que Rechercher ?', a: 'Rechercher vous permet de poser des questions cliniques en langage naturel. Vela cherche dans PubMed et synthétise une réponse graduée avec citations complètes.' },
      { q: 'Qu\u2019est-ce que Vérifier ?', a: 'Vérifier contrôle les interactions médicamenteuses à l\u2019aide des données officielles FDA drug labels (OpenFDA).' },
      { q: 'Qu\u2019est-ce que Expliquer ?', a: 'Expliquer vous aide à comprendre les rapports médicaux. Collez vos résultats ou téléchargez un rapport et Vela détaille chaque valeur en langage simple.' },
      { q: 'Que signifie la force de l\u2019évidence ?', a: 'Vela évalue chaque section selon la force des preuves. Preuves solides (vert), modérées (jaune) et limitées (rouge).' },
    ]},
    { title: 'Confidentialité et sécurité', items: [
      { q: 'Vela est-il un dispositif médical ?', a: 'Non. Vela est un outil de recherche et de référence. Il ne diagnostique pas, ne traite pas et ne fournit pas de conseils médicaux.' },
      { q: 'Vela protège-t-il mes données ?', a: 'Vela détecte et bloque activement les identifiants de santé personnels (PHI) avant de traiter toute requête. L\u2019historique est automatiquement supprimé après 180 jours.' },
      { q: 'Qui a créé Vela ?', a: 'Vela est créé par an-tho (an-tho.com), une entreprise axée sur les systèmes d\u2019aide à la décision basés sur les preuves.' },
    ]},
    { title: 'Tarifs', items: [
      { q: 'Combien coûte Vela ?', a: 'Vela propose un plan gratuit avec des requêtes quotidiennes limitées. Le plan Pro est à 9,99 $/mois ou 89,99 $/an (économisez 25 %).' },
      { q: 'Que comprend le plan gratuit ?', a: 'Le plan gratuit donne accès aux trois fonctionnalités avec un nombre limité de requêtes par jour. Pas de carte bancaire requise.' },
      { q: 'Que comprend Pro ?', a: 'Pro comprend des requêtes illimitées, le téléchargement PDF et images, l\u2019export PDF et l\u2019accès prioritaire aux nouvelles fonctionnalités.' },
      { q: 'Puis-je annuler à tout moment ?', a: 'Oui. Vous pouvez annuler votre abonnement Pro à tout moment depuis les paramètres de votre compte. Sans frais d\u2019annulation.' },
    ]},
  ],
  de: [
    { title: 'Über Vela', items: [
      { q: 'Was ist Vela?', a: 'Vela ist eine klinische Wissensmaschine für Fachkräfte im Gesundheitswesen. Es durchsucht über 36 Millionen PubMed-Artikel, prüft Arzneimittelinteraktionen mit offiziellen FDA-Daten und erklärt medizinische Berichte — in 16 Sprachen.' },
      { q: 'Warum werden Velas Antworten mit Quellen belegt?', a: 'Jede Antwort ist auf PubMed, FDA oder LOINC zurückführbar. Sie können jede Behauptung überprüfen, indem Sie auf die Originalquelle klicken.' },
      { q: 'Welche Datenquellen verwendet Vela?', a: 'Vela integriert drei maßgebliche medizinische Datenbanken: PubMed, FDA drug labels (OpenFDA) und LOINC/MedlinePlus.' },
      { q: 'Welche Sprachen unterstützt Vela?', a: 'Vela unterstützt 16 Sprachen: Englisch, Traditionelles Chinesisch, Vereinfachtes Chinesisch, Japanisch, Koreanisch, Thai, Spanisch, Französisch, Deutsch, Portugiesisch, Indonesisch, Vietnamesisch, Arabisch, Hindi, Bengalisch und Hebräisch.' },
    ]},
    { title: 'Funktionen', items: [
      { q: 'Was ist Forschung?', a: 'Forschung ermöglicht klinische Fragen in natürlicher Sprache. Vela durchsucht PubMed und erstellt eine evidenzbasierte Antwort mit vollständigen Zitaten.' },
      { q: 'Was ist Prüfung?', a: 'Prüfung überprüft Arzneimittelinteraktionen anhand offizieller FDA-Arzneimitteldaten (OpenFDA).' },
      { q: 'Was ist Erklärung?', a: 'Erklärung hilft beim Verständnis medizinischer Berichte. Fügen Sie Laborergebnisse ein oder laden Sie einen Bericht hoch, und Vela erklärt jeden Wert verständlich.' },
      { q: 'Was bedeutet Evidenzstärke?', a: 'Vela bewertet jeden Abschnitt nach der Stärke der unterstützenden Evidenz. Stark (grün), moderat (gelb) und begrenzt (rot).' },
    ]},
    { title: 'Datenschutz und Sicherheit', items: [
      { q: 'Ist Vela ein Medizinprodukt?', a: 'Nein. Vela ist ein Recherche- und Nachschlagetool. Es diagnostiziert nicht, behandelt nicht und gibt keine medizinischen Ratschläge.' },
      { q: 'Schützt Vela meine Daten?', a: 'Vela erkennt und blockiert aktiv persönliche Gesundheitsidentifikatoren (PHI) vor der Verarbeitung. Der Chatverlauf wird nach 180 Tagen automatisch gelöscht.' },
      { q: 'Wer hat Vela entwickelt?', a: 'Vela wurde von an-tho (an-tho.com) entwickelt, einem Unternehmen für evidenzbasierte Entscheidungsunterstützungssysteme.' },
    ]},
    { title: 'Preise', items: [
      { q: 'Was kostet Vela?', a: 'Vela bietet einen kostenlosen Plan mit begrenzten täglichen Abfragen. Der Pro-Plan kostet 9,99 $/Monat oder 89,99 $/Jahr (25 % sparen).' },
      { q: 'Was ist im kostenlosen Plan enthalten?', a: 'Der kostenlose Plan bietet Zugang zu allen drei Funktionen mit einer begrenzten Anzahl täglicher Abfragen. Keine Kreditkarte erforderlich.' },
      { q: 'Was ist in Pro enthalten?', a: 'Pro umfasst unbegrenzte Abfragen, PDF- und Bild-Upload, PDF-Export und bevorzugten Zugang zu neuen Funktionen.' },
      { q: 'Kann ich jederzeit kündigen?', a: 'Ja. Sie können Ihr Pro-Abonnement jederzeit in den Kontoeinstellungen kündigen. Keine Kündigungsgebühren.' },
    ]},
  ],
  it: [
    { title: 'Informazioni su Vela', items: [
      { q: 'Cos\u2019è Vela?', a: 'Vela è un motore di conoscenza clinica per professionisti sanitari. Cerca in oltre 40 milioni di articoli PubMed, verifica le interazioni farmacologiche con dati FDA ufficiali e spiega i referti medici — in 16 lingue.' },
      { q: 'Perché le risposte di Vela citano le fonti?', a: 'Ogni risposta è tracciabile fino a PubMed, FDA o LOINC. È possibile verificare qualsiasi affermazione cliccando sulla fonte originale.' },
      { q: 'Quali fonti di dati utilizza Vela?', a: 'Vela integra tre database medici autorevoli: PubMed, FDA drug labels (OpenFDA) e LOINC/MedlinePlus.' },
      { q: 'Quali lingue supporta Vela?', a: 'Vela supporta 16 lingue: inglese, cinese tradizionale, cinese semplificato, giapponese, coreano, tailandese, spagnolo, francese, tedesco, portoghese, indonesiano, vietnamita, arabo, hindi, bengalese ed ebraico.' },
    ]},
    { title: 'Funzionalità', items: [
      { q: 'Cos\u2019è Ricerca?', a: 'Ricerca consente di porre domande cliniche in linguaggio naturale. Vela cerca su PubMed e sintetizza una risposta graduata con citazioni complete.' },
      { q: 'Cos\u2019è Verifica?', a: 'Verifica controlla le interazioni farmacologiche utilizzando i dati ufficiali FDA drug labels (OpenFDA).' },
      { q: 'Cos\u2019è Spiega?', a: 'Spiega aiuta a comprendere i referti medici. Incolla i tuoi risultati o carica un referto e Vela spiega ogni valore in linguaggio semplice.' },
      { q: 'Cosa significa forza dell\u2019evidenza?', a: 'Vela valuta ogni sezione in base alla forza delle prove. Forte (verde), moderata (giallo) e limitata (rosso).' },
    ]},
    { title: 'Privacy e sicurezza', items: [
      { q: 'Vela è un dispositivo medico?', a: 'No. Vela è uno strumento di ricerca e riferimento. Non diagnostica, tratta né fornisce consulenza medica.' },
      { q: 'Vela protegge i miei dati?', a: 'Vela rileva e blocca attivamente gli identificatori sanitari personali (PHI) prima di elaborare qualsiasi query. La cronologia viene eliminata automaticamente dopo 180 giorni.' },
      { q: 'Chi ha creato Vela?', a: 'Vela è stata creata da an-tho (an-tho.com), un\u2019azienda focalizzata su sistemi di supporto decisionale basati su evidenze.' },
    ]},
    { title: 'Prezzi', items: [
      { q: 'Quanto costa Vela?', a: 'Vela offre un piano gratuito con query giornaliere limitate. Il piano Pro costa $9,99/mese o $89,99/anno (risparmia 25%).' },
      { q: 'Cosa include il piano gratuito?', a: 'Il piano gratuito include l\u2019accesso a tutte e tre le funzionalità con query giornaliere limitate. Nessuna carta di credito richiesta.' },
      { q: 'Cosa include Pro?', a: 'Pro include query illimitate, caricamento PDF e immagini, esportazione PDF e accesso prioritario a nuove funzionalità.' },
      { q: 'Posso cancellare in qualsiasi momento?', a: 'Sì. Puoi cancellare l\u2019abbonamento Pro in qualsiasi momento dalle impostazioni dell\u2019account. Nessun costo di cancellazione.' },
    ]},
  ],
  pt: [
    { title: 'Sobre o Vela', items: [
      { q: 'O que é o Vela?', a: 'Vela é um motor de conhecimento clínico para profissionais de saúde. Pesquisa mais de 40 milhões de artigos PubMed, verifica interações medicamentosas com dados oficiais da FDA e explica relatórios médicos — em 16 idiomas.' },
      { q: 'Por que as respostas do Vela incluem fontes?', a: 'Cada resposta é rastreável até PubMed, FDA ou LOINC. Você pode verificar qualquer afirmação clicando na fonte original.' },
      { q: 'Quais fontes de dados o Vela usa?', a: 'Vela integra três bancos de dados médicos autorizados: PubMed, FDA drug labels (OpenFDA) e LOINC/MedlinePlus.' },
      { q: 'Quais idiomas o Vela suporta?', a: 'Vela suporta 16 idiomas: inglês, chinês tradicional, chinês simplificado, japonês, coreano, tailandês, espanhol, francês, alemão, português, indonésio, vietnamita, árabe, hindi, bengali e hebraico.' },
    ]},
    { title: 'Recursos', items: [
      { q: 'O que é Pesquisar?', a: 'Pesquisar permite fazer perguntas clínicas em linguagem natural. O Vela busca no PubMed e sintetiza uma resposta graduada com citações completas.' },
      { q: 'O que é Verificar?', a: 'Verificar checa interações medicamentosas usando dados oficiais do FDA drug labels (OpenFDA).' },
      { q: 'O que é Explicar?', a: 'Explicar ajuda a entender relatórios médicos. Cole seus resultados ou envie um relatório e o Vela explica cada valor em linguagem simples.' },
      { q: 'O que significa força da evidência?', a: 'Vela classifica cada seção pela força das evidências. Forte (verde), moderada (amarelo) e limitada (vermelho).' },
    ]},
    { title: 'Privacidade e segurança', items: [
      { q: 'O Vela é um dispositivo médico?', a: 'Não. Vela é uma ferramenta de pesquisa e referência. Não diagnostica, trata nem fornece aconselhamento médico.' },
      { q: 'O Vela protege meus dados?', a: 'Vela detecta e bloqueia ativamente identificadores de saúde pessoal (PHI) antes de processar qualquer consulta. O histórico é excluído automaticamente após 180 dias.' },
      { q: 'Quem criou o Vela?', a: 'Vela foi criado pela an-tho (an-tho.com), uma empresa focada em sistemas de apoio à decisão baseados em evidências.' },
    ]},
    { title: 'Preços', items: [
      { q: 'Quanto custa o Vela?', a: 'Vela oferece um plano gratuito com consultas diárias limitadas. O plano Pro custa $9,99/mês ou $89,99/ano (economize 25%).' },
      { q: 'O que está incluído no plano gratuito?', a: 'O plano gratuito inclui acesso a todos os três recursos com consultas diárias limitadas. Sem cartão de crédito.' },
      { q: 'O que está incluído no Pro?', a: 'Pro inclui consultas ilimitadas, upload de PDF e imagens, exportação PDF e acesso prioritário a novos recursos.' },
      { q: 'Posso cancelar a qualquer momento?', a: 'Sim. Você pode cancelar sua assinatura Pro a qualquer momento nas configurações da conta. Sem taxas de cancelamento.' },
    ]},
  ],
  th: [
    { title: 'เกี่ยวกับ Vela', items: [
      { q: 'Vela คืออะไร?', a: 'Vela เป็นเครื่องมือความรู้ทางคลินิกสำหรับบุคลากรทางการแพทย์ ค้นหาบทความ PubMed กว่า 40 ล้านบทความ ตรวจสอบปฏิกิริยาระหว่างยากับข้อมูล FDA อย่างเป็นทางการ และอธิบายรายงานทางการแพทย์ — รองรับ 16 ภาษา' },
      { q: 'ทำไมคำตอบของ Vela จึงมีการอ้างอิงแหล่งที่มา?', a: 'ทุกคำตอบสามารถสืบย้อนไปยัง PubMed, FDA หรือ LOINC ได้ คุณสามารถตรวจสอบได้โดยคลิกที่แหล่งที่มาต้นฉบับ' },
      { q: 'Vela ใช้แหล่งข้อมูลใด?', a: 'Vela รวมฐานข้อมูลทางการแพทย์ที่เชื่อถือได้สามแห่ง: PubMed, FDA drug labels (OpenFDA) และ LOINC/MedlinePlus' },
      { q: 'Vela รองรับภาษาใดบ้าง?', a: 'Vela รองรับ 16 ภาษา: อังกฤษ, จีนดั้งเดิม, จีนตัวย่อ, ญี่ปุ่น, เกาหลี, ไทย, สเปน, ฝรั่งเศส, เยอรมัน, โปรตุเกส, อินโดนีเซีย, เวียดนาม, อาหรับ, ฮินดี, เบงกาลี และฮีบรู' },
    ]},
    { title: 'คุณสมบัติ', items: [
      { q: 'วิจัย คืออะไร?', a: 'วิจัยช่วยให้คุณถามคำถามทางคลินิกด้วยภาษาธรรมชาติ Vela ค้นหา PubMed และสังเคราะห์คำตอบที่มีการจัดระดับหลักฐานพร้อมการอ้างอิง' },
      { q: 'ตรวจสอบ คืออะไร?', a: 'ตรวจสอบปฏิกิริยาระหว่างยาโดยใช้ข้อมูล FDA drug labels (OpenFDA) อย่างเป็นทางการ' },
      { q: 'อธิบาย คืออะไร?', a: 'อธิบายช่วยให้คุณเข้าใจรายงานทางการแพทย์ วางผลตรวจหรืออัปโหลดรายงาน แล้ว Vela จะอธิบายแต่ละค่าด้วยภาษาที่เข้าใจง่าย' },
      { q: 'ความแข็งแกร่งของหลักฐาน หมายความว่าอะไร?', a: 'Vela ให้คะแนนแต่ละส่วนตามความแข็งแกร่งของหลักฐาน แข็งแกร่ง (เขียว), ปานกลาง (เหลือง) และจำกัด (แดง)' },
    ]},
    { title: 'ความเป็นส่วนตัวและความปลอดภัย', items: [
      { q: 'Vela เป็นอุปกรณ์ทางการแพทย์หรือไม่?', a: 'ไม่ Vela เป็นเครื่องมือวิจัยและอ้างอิง ไม่ได้วินิจฉัย รักษา หรือให้คำแนะนำทางการแพทย์' },
      { q: 'Vela ปกป้องข้อมูลของฉันหรือไม่?', a: 'Vela ตรวจจับและบล็อกข้อมูลระบุตัวตนด้านสุขภาพ (PHI) ก่อนประมวลผล ประวัติจะถูกลบอัตโนมัติหลัง 180 วัน' },
      { q: 'ใครสร้าง Vela?', a: 'Vela สร้างโดย an-tho (an-tho.com) บริษัทที่มุ่งเน้นระบบสนับสนุนการตัดสินใจที่อิงหลักฐาน' },
    ]},
    { title: 'ราคา', items: [
      { q: 'Vela ราคาเท่าไร?', a: 'Vela มีแผนฟรีพร้อมคำถามจำกัดต่อวัน แผน Pro ราคา $9.99/เดือน หรือ $89.99/ปี (ประหยัด 25%)' },
      { q: 'แผนฟรีรวมอะไรบ้าง?', a: 'แผนฟรีให้เข้าถึงทั้ง 3 ฟีเจอร์ พร้อมจำนวนคำถามจำกัดต่อวัน ไม่ต้องใช้บัตรเครดิต' },
      { q: 'Pro รวมอะไรบ้าง?', a: 'Pro รวมคำถามไม่จำกัด อัปโหลด PDF และรูปภาพ ส่งออก PDF และสิทธิ์เข้าถึงฟีเจอร์ใหม่ก่อน' },
      { q: 'ยกเลิกได้ตลอดเวลาหรือไม่?', a: 'ได้ คุณสามารถยกเลิกสมาชิก Pro ได้ตลอดเวลาจากการตั้งค่าบัญชี ไม่มีค่าธรรมเนียมยกเลิก' },
    ]},
  ],
  ar: [
    { title: 'حول Vela', items: [
      { q: 'ما هو Vela؟', a: 'Vela هو محرك معرفة سريري لمتخصصي الرعاية الصحية. يبحث في أكثر من 40 مليون مقال في PubMed، ويتحقق من تفاعلات الأدوية مع بيانات FDA الرسمية، ويشرح التقارير الطبية — بـ 16 لغة.' },
      { q: 'لماذا تتضمن إجابات Vela مصادر؟', a: 'كل إجابة قابلة للتتبع إلى PubMed أو FDA أو LOINC. يمكنك التحقق بالنقر على المصدر الأصلي.' },
      { q: 'ما مصادر البيانات التي يستخدمها Vela؟', a: 'يدمج Vela ثلاث قواعد بيانات طبية موثوقة: PubMed و FDA drug labels (OpenFDA) و LOINC/MedlinePlus.' },
      { q: 'ما اللغات التي يدعمها Vela؟', a: 'يدعم Vela 16 لغة: الإنجليزية، الصينية التقليدية، الصينية المبسطة، اليابانية، الكورية، التايلاندية، الإسبانية، الفرنسية، الألمانية، البرتغالية، الإندونيسية، الفيتنامية، العربية، الهندية، البنغالية والعبرية.' },
    ]},
    { title: 'الميزات', items: [
      { q: 'ما هو البحث؟', a: 'يتيح لك البحث طرح أسئلة سريرية بلغة طبيعية. يبحث Vela في PubMed ويقدم إجابة مصنفة بالأدلة مع اقتباسات كاملة.' },
      { q: 'ما هو التحقق؟', a: 'يتحقق من تفاعلات الأدوية باستخدام بيانات FDA drug labels (OpenFDA) الرسمية.' },
      { q: 'ما هو الشرح؟', a: 'يساعدك الشرح على فهم التقارير الطبية. الصق نتائجك أو ارفع تقريراً ويوضح Vela كل قيمة بلغة بسيطة.' },
      { q: 'ماذا تعني قوة الدليل؟', a: 'يقيّم Vela كل قسم حسب قوة الأدلة الداعمة. قوي (أخضر)، معتدل (أصفر) ومحدود (أحمر).' },
    ]},
    { title: 'الخصوصية والأمان', items: [
      { q: 'هل Vela جهاز طبي؟', a: 'لا. Vela أداة بحث ومرجعية. لا يشخص أو يعالج أو يقدم نصائح طبية.' },
      { q: 'هل يحمي Vela بياناتي؟', a: 'يكتشف Vela ويحظر معرفات الصحة الشخصية (PHI) قبل معالجة أي استعلام. يتم حذف السجل تلقائياً بعد 180 يوماً.' },
      { q: 'من بنى Vela؟', a: 'بُني Vela بواسطة an-tho (an-tho.com)، شركة تركز على أنظمة دعم القرار القائمة على الأدلة.' },
    ]},
    { title: 'الأسعار', items: [
      { q: 'كم يكلف Vela؟', a: 'يقدم Vela خطة مجانية مع استعلامات يومية محدودة. خطة Pro بسعر $9.99/شهر أو $89.99/سنة (وفر 25%).' },
      { q: 'ماذا تتضمن الخطة المجانية؟', a: 'الخطة المجانية تشمل الوصول لجميع الميزات الثلاث مع عدد محدود من الاستعلامات يومياً. بدون بطاقة ائتمان.' },
      { q: 'ماذا يتضمن Pro؟', a: 'يشمل Pro استعلامات غير محدودة، رفع PDF وصور، تصدير PDF وأولوية الوصول للميزات الجديدة.' },
      { q: 'هل يمكنني الإلغاء في أي وقت؟', a: 'نعم. يمكنك إلغاء اشتراك Pro في أي وقت من إعدادات حسابك. بدون رسوم إلغاء.' },
    ]},
  ],
  hi: [
    { title: 'Vela के बारे में', items: [
      { q: 'Vela क्या है?', a: 'Vela स्वास्थ्य पेशेवरों के लिए एक क्लिनिकल ज्ञान इंजन है। यह PubMed के 36 मिलियन+ लेखों में खोज करता है, FDA आधिकारिक डेटा से दवा इंटरैक्शन की जांच करता है, और LOINC, RxNorm और MedlinePlus मानकों का उपयोग करके मेडिकल रिपोर्ट समझाता है — 16 भाषाओं में।' },
      { q: 'Vela के उत्तर स्रोतों के साथ क्यों होते हैं?', a: 'हर उत्तर PubMed, FDA या LOINC तक ट्रेस किया जा सकता है। आप मूल स्रोत पर क्लिक करके किसी भी दावे को सत्यापित कर सकते हैं।' },
      { q: 'Vela किन डेटा स्रोतों का उपयोग करता है?', a: 'Vela तीन प्रामाणिक चिकित्सा डेटाबेस को एकीकृत करता है: PubMed, FDA drug labels (OpenFDA) और LOINC/MedlinePlus।' },
      { q: 'Vela किन भाषाओं का समर्थन करता है?', a: 'Vela 16 भाषाओं का समर्थन करता है: अंग्रेजी, पारंपरिक चीनी, सरलीकृत चीनी, जापानी, कोरियाई, थाई, स्पेनिश, फ्रेंच, जर्मन, पुर्तगाली, इंडोनेशियाई, वियतनामी, अरबी, हिंदी, बंगाली और हिब्रू।' },
    ]},
    { title: 'सुविधाएँ', items: [
      { q: 'शोध क्या है?', a: 'शोध आपको प्राकृतिक भाषा में क्लिनिकल प्रश्न पूछने देता है। Vela PubMed में खोज करता है और पूर्ण उद्धरणों के साथ साक्ष्य-आधारित उत्तर प्रदान करता है।' },
      { q: 'सत्यापन क्या है?', a: 'सत्यापन FDA drug labels (OpenFDA) आधिकारिक डेटा का उपयोग करके दवा इंटरैक्शन की जांच करता है।' },
      { q: 'व्याख्या क्या है?', a: 'व्याख्या मेडिकल रिपोर्ट समझने में मदद करती है। अपने परिणाम पेस्ट करें या रिपोर्ट अपलोड करें और Vela प्रत्येक मान को सरल भाषा में समझाएगा।' },
      { q: 'साक्ष्य शक्ति का क्या अर्थ है?', a: 'Vela प्रत्येक अनुभाग को साक्ष्य की शक्ति के अनुसार रेट करता है। मजबूत (हरा), मध्यम (पीला) और सीमित (लाल)।' },
    ]},
    { title: 'गोपनीयता और सुरक्षा', items: [
      { q: 'क्या Vela एक चिकित्सा उपकरण है?', a: 'नहीं। Vela एक शोध और संदर्भ उपकरण है। यह निदान, उपचार या चिकित्सा सलाह प्रदान नहीं करता।' },
      { q: 'क्या Vela मेरा डेटा सुरक्षित रखता है?', a: 'Vela किसी भी क्वेरी को प्रोसेस करने से पहले व्यक्तिगत स्वास्थ्य पहचानकर्ता (PHI) को सक्रिय रूप से पहचानता और ब्लॉक करता है। इतिहास 180 दिनों के बाद स्वचालित रूप से हटा दिया जाता है।' },
      { q: 'Vela किसने बनाया?', a: 'Vela an-tho (an-tho.com) द्वारा बनाया गया है, जो साक्ष्य-आधारित निर्णय समर्थन प्रणालियों पर केंद्रित कंपनी है।' },
    ]},
    { title: 'मूल्य निर्धारण', items: [
      { q: 'Vela की कीमत कितनी है?', a: 'Vela सीमित दैनिक क्वेरी वाला मुफ्त प्लान प्रदान करता है। Pro प्लान $9.99/माह या $89.99/वर्ष (25% बचत) है।' },
      { q: 'मुफ्त प्लान में क्या शामिल है?', a: 'मुफ्त प्लान में तीनों सुविधाओं तक सीमित दैनिक क्वेरी के साथ पहुंच शामिल है। क्रेडिट कार्ड आवश्यक नहीं।' },
      { q: 'Pro में क्या शामिल है?', a: 'Pro में असीमित क्वेरी, PDF और छवि अपलोड, PDF निर्यात और नई सुविधाओं तक प्राथमिकता पहुंच शामिल है।' },
      { q: 'क्या मैं कभी भी रद्द कर सकता हूं?', a: 'हां। आप अपने खाते की सेटिंग से कभी भी Pro सदस्यता रद्द कर सकते हैं। कोई रद्दीकरण शुल्क नहीं।' },
    ]},
  ],
  bn: [
    { title: 'Vela সম্পর্কে', items: [
      { q: 'Vela কী?', a: 'Vela স্বাস্থ্যসেবা পেশাদারদের জন্য একটি ক্লিনিক্যাল জ্ঞান ইঞ্জিন। এটি PubMed-এর 36 মিলিয়ন+ নিবন্ধ অনুসন্ধান করে, FDA অফিসিয়াল ডেটা দিয়ে ওষুধের মিথস্ক্রিয়া যাচাই করে এবং মেডিকেল রিপোর্ট ব্যাখ্যা করে — 16টি ভাষায়।' },
      { q: 'Vela-র উত্তরে উৎস কেন থাকে?', a: 'প্রতিটি উত্তর PubMed, FDA বা LOINC-এ ট্রেস করা যায়। আপনি মূল উৎসে ক্লিক করে যেকোনো দাবি যাচাই করতে পারেন।' },
      { q: 'Vela কোন ডেটা উৎস ব্যবহার করে?', a: 'Vela তিনটি প্রামাণিক মেডিকেল ডেটাবেস সংহত করে: PubMed, FDA drug labels (OpenFDA) এবং LOINC/MedlinePlus।' },
      { q: 'Vela কোন ভাষা সমর্থন করে?', a: 'Vela 16টি ভাষা সমর্থন করে: ইংরেজি, ঐতিহ্যবাহী চীনা, সরলীকৃত চীনা, জাপানি, কোরিয়ান, থাই, স্প্যানিশ, ফরাসি, জার্মান, পর্তুগিজ, ইন্দোনেশিয়, ভিয়েতনামি, আরবি, হিন্দি, বাংলা এবং হিব্রু।' },
    ]},
    { title: 'বৈশিষ্ট্য', items: [
      { q: 'গবেষণা কী?', a: 'গবেষণা আপনাকে প্রাকৃতিক ভাষায় ক্লিনিক্যাল প্রশ্ন জিজ্ঞাসা করতে দেয়। Vela PubMed-এ অনুসন্ধান করে এবং সম্পূর্ণ উদ্ধৃতিসহ প্রমাণ-ভিত্তিক উত্তর প্রদান করে।' },
      { q: 'যাচাই কী?', a: 'যাচাই FDA drug labels (OpenFDA) অফিসিয়াল ডেটা ব্যবহার করে ওষুধের মিথস্ক্রিয়া পরীক্ষা করে।' },
      { q: 'ব্যাখ্যা কী?', a: 'ব্যাখ্যা মেডিকেল রিপোর্ট বুঝতে সাহায্য করে। আপনার ফলাফল পেস্ট করুন বা রিপোর্ট আপলোড করুন এবং Vela প্রতিটি মান সহজ ভাষায় ব্যাখ্যা করবে।' },
      { q: 'প্রমাণের শক্তি কী মানে?', a: 'Vela প্রতিটি বিভাগকে সমর্থনকারী প্রমাণের শক্তি অনুসারে মূল্যায়ন করে। শক্তিশালী (সবুজ), মাঝারি (হলুদ) এবং সীমিত (লাল)।' },
    ]},
    { title: 'গোপনীয়তা ও নিরাপত্তা', items: [
      { q: 'Vela কি একটি চিকিৎসা যন্ত্র?', a: 'না। Vela একটি গবেষণা ও রেফারেন্স সরঞ্জাম। এটি রোগ নির্ণয়, চিকিৎসা বা চিকিৎসা পরামর্শ দেয় না।' },
      { q: 'Vela কি আমার ডেটা সুরক্ষিত রাখে?', a: 'Vela যেকোনো কোয়েরি প্রক্রিয়া করার আগে ব্যক্তিগত স্বাস্থ্য শনাক্তকারী (PHI) সক্রিয়ভাবে সনাক্ত ও ব্লক করে। ইতিহাস 180 দিন পরে স্বয়ংক্রিয়ভাবে মুছে ফেলা হয়।' },
      { q: 'Vela কে তৈরি করেছে?', a: 'Vela an-tho (an-tho.com) দ্বারা তৈরি, প্রমাণ-ভিত্তিক সিদ্ধান্ত সহায়তা সিস্টেমে নিবেদিত একটি কোম্পানি।' },
    ]},
    { title: 'মূল্য নির্ধারণ', items: [
      { q: 'Vela-র দাম কত?', a: 'Vela সীমিত দৈনিক কোয়েরি সহ বিনামূল্যে প্ল্যান অফার করে। Pro প্ল্যান $9.99/মাস বা $89.99/বছর (25% সাশ্রয়)।' },
      { q: 'বিনামূল্যে প্ল্যানে কী অন্তর্ভুক্ত?', a: 'বিনামূল্যে প্ল্যানে তিনটি বৈশিষ্ট্যে সীমিত দৈনিক কোয়েরি অন্তর্ভুক্ত। ক্রেডিট কার্ড প্রয়োজন নেই।' },
      { q: 'Pro-তে কী অন্তর্ভুক্ত?', a: 'Pro-তে সীমাহীন কোয়েরি, PDF ও ছবি আপলোড, PDF রপ্তানি এবং নতুন বৈশিষ্ট্যে অগ্রাধিকার অ্যাক্সেস অন্তর্ভুক্ত।' },
      { q: 'যেকোনো সময় বাতিল করতে পারি?', a: 'হ্যাঁ। আপনি অ্যাকাউন্ট সেটিংস থেকে যেকোনো সময় Pro সাবস্ক্রিপশন বাতিল করতে পারেন। কোনো বাতিলকরণ ফি নেই।' },
    ]},
  ],
  he: [
    { title: 'אודות Vela', items: [
      { q: 'מה זה Vela?', a: 'Vela הוא מנוע ידע קליני לאנשי מקצוע בתחום הבריאות. הוא מחפש ביותר מ-40 מיליון מאמרי PubMed, בודק אינטראקציות תרופתיות עם נתוני FDA רשמיים ומסביר דוחות רפואיים — ב-16 שפות.' },
      { q: 'למה תשובות Vela מצוטטות עם מקורות?', a: 'כל תשובה ניתנת למעקב עד PubMed, FDA או LOINC. ניתן לאמת כל טענה בלחיצה על המקור המקורי.' },
      { q: 'באילו מקורות נתונים Vela משתמש?', a: 'Vela משלב שלושה מסדי נתונים רפואיים סמכותיים: PubMed, FDA drug labels (OpenFDA) ו-LOINC/MedlinePlus.' },
      { q: 'אילו שפות Vela תומך?', a: 'Vela תומך ב-16 שפות: אנגלית, סינית מסורתית, סינית מפושטת, יפנית, קוריאנית, תאילנדית, ספרדית, צרפתית, גרמנית, פורטוגזית, אינדונזית, וייטנאמית, ערבית, הינדי, בנגלית ועברית.' },
    ]},
    { title: 'תכונות', items: [
      { q: 'מה זה מחקר?', a: 'מחקר מאפשר לשאול שאלות קליניות בשפה טבעית. Vela מחפש ב-PubMed ומסנתז תשובה מדורגת עם ציטוטים מלאים.' },
      { q: 'מה זה אימות?', a: 'אימות בודק אינטראקציות תרופתיות באמצעות נתוני FDA drug labels (OpenFDA) הרשמיים.' },
      { q: 'מה זה הסבר?', a: 'הסבר עוזר להבין דוחות רפואיים. הדבק את תוצאותיך או העלה דוח ו-Vela יסביר כל ערך בשפה פשוטה.' },
      { q: 'מה המשמעות של עוצמת ראיות?', a: 'Vela מדרג כל קטע לפי עוצמת הראיות. חזק (ירוק), בינוני (צהוב) ומוגבל (אדום).' },
    ]},
    { title: 'פרטיות ואבטחה', items: [
      { q: 'האם Vela הוא מכשיר רפואי?', a: 'לא. Vela הוא כלי מחקר ועיון. הוא אינו מאבחן, מטפל או מספק ייעוץ רפואי.' },
      { q: 'האם Vela מגן על הנתונים שלי?', a: 'Vela מזהה וחוסם באופן פעיל מזהי בריאות אישיים (PHI) לפני עיבוד כל שאילתה. ההיסטוריה נמחקת אוטומטית לאחר 180 יום.' },
      { q: 'מי בנה את Vela?', a: 'Vela נבנה על ידי an-tho (an-tho.com), חברה המתמקדת במערכות תמיכה בהחלטות מבוססות ראיות.' },
    ]},
    { title: 'תמחור', items: [
      { q: 'כמה עולה Vela?', a: 'Vela מציע תוכנית חינמית עם שאילתות יומיות מוגבלות. תוכנית Pro בעלות $9.99/חודש או $89.99/שנה (חסכו 25%).' },
      { q: 'מה כלול בתוכנית החינמית?', a: 'התוכנית החינמית כוללת גישה לשלוש התכונות עם שאילתות יומיות מוגבלות. ללא כרטיס אשראי.' },
      { q: 'מה כלול ב-Pro?', a: 'Pro כולל שאילתות ללא הגבלה, העלאת PDF ותמונות, ייצוא PDF וגישה מועדפת לתכונות חדשות.' },
      { q: 'אפשר לבטל בכל עת?', a: 'כן. ניתן לבטל את מנוי Pro בכל עת מהגדרות החשבון. ללא דמי ביטול.' },
    ]},
  ],
  vi: [
    { title: 'Về Vela', items: [
      { q: 'Vela là gì?', a: 'Vela là công cụ tri thức lâm sàng cho chuyên gia y tế. Tìm kiếm hơn 40 triệu bài viết PubMed, kiểm tra tương tác thuốc với dữ liệu FDA chính thức và giải thích báo cáo y tế — hỗ trợ 16 ngôn ngữ.' },
      { q: 'Tại sao câu trả lời của Vela có trích dẫn nguồn?', a: 'Mọi câu trả lời đều có thể truy nguyên đến PubMed, FDA hoặc LOINC. Bạn có thể xác minh bằng cách nhấp vào nguồn gốc.' },
      { q: 'Vela sử dụng nguồn dữ liệu nào?', a: 'Vela tích hợp ba cơ sở dữ liệu y khoa uy tín: PubMed, FDA drug labels (OpenFDA) và LOINC/MedlinePlus.' },
      { q: 'Vela hỗ trợ ngôn ngữ nào?', a: 'Vela hỗ trợ 16 ngôn ngữ: Anh, Trung phồn thể, Trung giản thể, Nhật, Hàn, Thái, Tây Ban Nha, Pháp, Đức, Bồ Đào Nha, Indonesia, Việt, Ả Rập, Hindi, Bengal và Hebrew.' },
    ]},
    { title: 'Tính năng', items: [
      { q: 'Nghiên cứu là gì?', a: 'Nghiên cứu cho phép bạn đặt câu hỏi lâm sàng bằng ngôn ngữ tự nhiên. Vela tìm kiếm PubMed và tổng hợp câu trả lời có xếp hạng bằng chứng với trích dẫn đầy đủ.' },
      { q: 'Xác minh là gì?', a: 'Xác minh kiểm tra tương tác thuốc sử dụng dữ liệu FDA drug labels (OpenFDA) chính thức.' },
      { q: 'Giải thích là gì?', a: 'Giải thích giúp bạn hiểu báo cáo y tế. Dán kết quả hoặc tải lên báo cáo và Vela sẽ giải thích từng giá trị bằng ngôn ngữ đơn giản.' },
      { q: 'Độ mạnh bằng chứng nghĩa là gì?', a: 'Vela đánh giá mỗi phần theo độ mạnh của bằng chứng. Mạnh (xanh), trung bình (vàng) và hạn chế (đỏ).' },
    ]},
    { title: 'Quyền riêng tư & An toàn', items: [
      { q: 'Vela có phải thiết bị y tế không?', a: 'Không. Vela là công cụ nghiên cứu và tham khảo. Không chẩn đoán, điều trị hoặc cung cấp tư vấn y khoa.' },
      { q: 'Vela có bảo vệ dữ liệu của tôi không?', a: 'Vela chủ động phát hiện và chặn thông tin nhận dạng sức khỏe cá nhân (PHI) trước khi xử lý. Lịch sử được tự động xóa sau 180 ngày.' },
      { q: 'Ai xây dựng Vela?', a: 'Vela được xây dựng bởi an-tho (an-tho.com), công ty chuyên về hệ thống hỗ trợ quyết định dựa trên bằng chứng.' },
    ]},
    { title: 'Bảng giá', items: [
      { q: 'Vela giá bao nhiêu?', a: 'Vela cung cấp gói miễn phí với truy vấn hàng ngày có giới hạn. Gói Pro $9,99/tháng hoặc $89,99/năm (tiết kiệm 25%).' },
      { q: 'Gói miễn phí bao gồm gì?', a: 'Gói miễn phí bao gồm truy cập cả ba tính năng với số lượng truy vấn hàng ngày có giới hạn. Không cần thẻ tín dụng.' },
      { q: 'Pro bao gồm gì?', a: 'Pro bao gồm truy vấn không giới hạn, tải lên PDF và hình ảnh, xuất PDF và quyền truy cập ưu tiên vào tính năng mới.' },
      { q: 'Tôi có thể hủy bất cứ lúc nào không?', a: 'Có. Bạn có thể hủy đăng ký Pro bất cứ lúc nào từ cài đặt tài khoản. Không phí hủy.' },
    ]},
  ],
};
