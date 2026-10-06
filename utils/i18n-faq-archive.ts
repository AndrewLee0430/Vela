// utils/i18n-faq-archive.ts — archive UI car (founder ruling U4, 2026-10-05).
// The FAQ shown INSTEAD of utils/i18n-faq.ts when the build carries
// NEXT_PUBLIC_ARCHIVE_MODE=true (pages/faq.tsx). en authored; zh-TW written natively;
// the other 14 are machine-translated and marked per cell.
// Q4's answer is NOT stored here: pages/faq.tsx reuses translations[lang].footerDisclaimer
// verbatim (utils/i18n.ts), per the ruling.
// Q5 is derived from code, not from policy text — derivation table in
// docs/batons/archive_ui_car_20261005.md. If the Research logging changes, re-derive Q5.
import type { LangCode } from './i18n';

export interface ArchiveFaqStrings {
  title: string;
  q1: string; a1: string;   // + link → /about/ (label: ui.archiveShowcaseLink)
  q2: string; a2: string;
  q3: string; a3: string;   // + link → /about/
  q4: string;               // answer = translations[lang].footerDisclaimer
  q5: string; a5: string;
  q6: string; a6: string;   // contact = the address published on /privacy (pages/privacy.tsx:48)
  q7: string; a7: string;   // + link → the repository
}

export const archiveFaqI18n: Record<LangCode, ArchiveFaqStrings> = {
  en: {
    title: 'Vela is archived',
    q1: 'What is Vela now?',
    a1: 'Vela was a multilingual medical search tool for healthcare professionals, built and run from February to October 2026. It is now an archived project: this site is a demo of Research only and is no longer maintained.',
    q2: 'Is it free?',
    a2: 'Yes. There are no accounts and no payments. The demo runs on a small daily usage budget, so it may pause until the next day once the budget is used up.',
    q3: 'What happened to Verify and Explain?',
    a3: 'Both were retired when Vela was archived. How they worked is described on the project page.',
    q4: 'Is this medical advice?',
    q5: 'What happens to my questions?',
    a5: 'Questions asked in the demo are not saved to a database, and Vela no longer has accounts. To answer a question, Vela sends it to OpenAI\'s language model and sends search terms derived from it to PubMed and openFDA. Vela\'s server logs record a question\'s length, not its text. To enforce the daily budget, Vela keeps a usage count under a one-way hashed identifier made from your IP address and browser session; the count holds no question text. Usage analytics record events, such as how many sources were cited, not the text you type.',
    q6: 'I had a subscription.',
    a6: 'All subscriptions have ended. For questions about a past payment, write to support@an-tho.com.',
    q7: 'Is the code available?',
    a7: 'Yes. The source code is on GitHub.',
  },
  'zh-TW': {
    title: 'Vela 已封存',
    q1: 'Vela 現在是什麼？',
    a1: 'Vela 是為醫療專業人員打造的多語言醫學搜尋工具，於 2026 年 2 月至 10 月間開發與營運。它現在是已封存的專案：這個網站只保留「研究」功能的展示，且已不再維護。',
    q2: '需要付費嗎？',
    a2: '不需要。沒有帳號，也不收費。展示版有每日使用預算，預算用完後可能會暫停到隔天。',
    q3: '「驗證」和「解讀」到哪裡去了？',
    a3: '這兩個功能已隨 Vela 封存而停用。它們的運作方式記錄在專案頁面上。',
    q4: '這是醫療建議嗎？',
    q5: '我的提問會怎麼處理？',
    a5: '在展示版中提出的問題不會存進資料庫，Vela 也已不再提供帳號。為了回答問題，Vela 會把問題傳送給 OpenAI 的語言模型，並把依據問題產生的搜尋詞傳送給 PubMed 與 openFDA。Vela 的伺服器記錄檔只記下問題的長度，不記下問題的文字。為了控管每日預算，Vela 會用一個由你的 IP 位址與瀏覽器工作階段經單向雜湊產生的識別碼來記錄使用次數，這個計數不含任何問題文字。使用分析只記錄事件（例如引用了幾個來源），不記錄你輸入的文字。',
    q6: '我之前有訂閱。',
    a6: '所有訂閱都已結束。如對過去的付款有疑問，請來信 support@an-tho.com。',
    q7: '可以取得原始碼嗎？',
    a7: '可以，原始碼放在 GitHub 上。',
  },
  'zh-CN': {
    title: 'Vela 已归档', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q1: 'Vela 现在是什么？', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a1: 'Vela 是为医疗专业人员打造的多语言医学搜索工具，于 2026 年 2 月至 10 月间开发和运营。它现在是已归档的项目：本网站仅保留“研究”功能的演示，且已不再维护。', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q2: '需要付费吗？', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a2: '不需要。没有账号，也不收费。演示版有每日使用预算，预算用完后可能会暂停到第二天。', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q3: '“验证”和“解读”去哪了？', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a3: '这两个功能已随 Vela 归档而停用。它们的工作方式记录在项目页面上。', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q4: '这是医疗建议吗？', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q5: '我的提问会如何处理？', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a5: '在演示版中提出的问题不会保存到数据库，Vela 也已不再提供账号。为了回答问题，Vela 会把问题发送给 OpenAI 的语言模型，并把根据问题生成的搜索词发送给 PubMed 和 openFDA。Vela 的服务器日志只记录问题的长度，不记录问题的文本。为了控制每日预算，Vela 会使用一个由你的 IP 地址和浏览器会话经单向哈希生成的标识符来记录使用次数，该计数不包含任何问题文本。使用分析只记录事件（例如引用了多少来源），不记录你输入的文字。', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q6: '我之前订阅过。', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a6: '所有订阅均已结束。如对过去的付款有疑问，请发邮件至 support@an-tho.com。', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q7: '可以获取源代码吗？', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a7: '可以，源代码在 GitHub 上。', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
  },
  ja: {
    title: 'Vela はアーカイブされました', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q1: 'Vela は今どうなっていますか？', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a1: 'Vela は医療従事者向けの多言語医学検索ツールで、2026 年 2 月から 10 月まで開発・運営されていました。現在はアーカイブされたプロジェクトで、このサイトは「研究」機能のみのデモであり、今後の保守は行われません。', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q2: '無料ですか？', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a2: 'はい。アカウントも支払いもありません。デモには 1 日の利用予算があり、予算を使い切ると翌日まで停止することがあります。', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q3: '「検証」と「解説」はどうなりましたか？', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a3: 'どちらも Vela のアーカイブに伴い終了しました。仕組みはプロジェクトページで説明しています。', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q4: 'これは医療アドバイスですか？', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q5: '私の質問はどのように扱われますか？', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a5: 'デモでの質問はデータベースに保存されず、Vela にはもうアカウントもありません。質問に答えるため、Vela は質問を OpenAI の言語モデルに送信し、質問から作成した検索語を PubMed と openFDA に送信します。Vela のサーバーログには質問の長さだけが記録され、文章は記録されません。1 日の予算を管理するため、Vela は IP アドレスとブラウザのセッションから一方向ハッシュで作成した識別子の下で利用回数を記録します。この回数に質問の文章は含まれません。利用状況の分析では、引用された情報源の数などのイベントを記録し、入力した文章は記録しません。', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q6: 'サブスクリプションを利用していました。', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a6: 'すべてのサブスクリプションは終了しました。過去のお支払いについてのご質問は support@an-tho.com までご連絡ください。', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q7: 'ソースコードは公開されていますか？', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a7: 'はい。ソースコードは GitHub にあります。', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
  },
  ko: {
    title: 'Vela는 보관되었습니다', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q1: 'Vela는 지금 어떤 상태인가요?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a1: 'Vela는 의료 전문가를 위한 다국어 의학 검색 도구로, 2026년 2월부터 10월까지 개발·운영되었습니다. 현재는 보관된 프로젝트이며, 이 사이트는 연구 기능만 제공하는 데모로 더 이상 유지 관리되지 않습니다.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q2: '무료인가요?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a2: '네. 계정도 결제도 없습니다. 데모에는 일일 사용 예산이 있어, 예산이 소진되면 다음 날까지 일시 중지될 수 있습니다.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q3: '확인과 설명 기능은 어떻게 되었나요?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a3: '두 기능 모두 Vela가 보관되면서 종료되었습니다. 작동 방식은 프로젝트 페이지에 설명되어 있습니다.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q4: '이것은 의학적 조언인가요?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q5: '제 질문은 어떻게 처리되나요?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a5: '데모에서 한 질문은 데이터베이스에 저장되지 않으며, Vela에는 더 이상 계정이 없습니다. 질문에 답하기 위해 Vela는 질문을 OpenAI의 언어 모델로 보내고, 질문을 바탕으로 만든 검색어를 PubMed와 openFDA로 보냅니다. Vela의 서버 로그에는 질문의 길이만 기록되고 질문 내용은 기록되지 않습니다. 일일 예산을 관리하기 위해 Vela는 IP 주소와 브라우저 세션을 단방향 해시로 변환한 식별자로 사용 횟수를 기록하며, 이 횟수에는 질문 내용이 포함되지 않습니다. 사용 분석은 인용된 출처 수와 같은 이벤트만 기록하며, 입력한 내용은 기록하지 않습니다.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q6: '구독을 이용하고 있었습니다.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a6: '모든 구독이 종료되었습니다. 과거 결제에 관한 문의는 support@an-tho.com으로 보내 주세요.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q7: '소스 코드를 볼 수 있나요?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a7: '네. 소스 코드는 GitHub에 있습니다.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
  },
  es: {
    title: 'Vela está archivado', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q1: '¿Qué es Vela ahora?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a1: 'Vela fue una herramienta de búsqueda médica multilingüe para profesionales de la salud, desarrollada y operada de febrero a octubre de 2026. Ahora es un proyecto archivado: este sitio es una demo solo de la función Investigar y ya no se mantiene.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q2: '¿Es gratis?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a2: 'Sí. No hay cuentas ni pagos. La demo funciona con un pequeño presupuesto de uso diario, así que puede pausarse hasta el día siguiente cuando se agote.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q3: '¿Qué pasó con Verificar y Explicar?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a3: 'Ambas se retiraron cuando Vela se archivó. Su funcionamiento se describe en la página del proyecto.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q4: '¿Esto es consejo médico?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q5: '¿Qué pasa con mis preguntas?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a5: 'Las preguntas hechas en la demo no se guardan en una base de datos, y Vela ya no tiene cuentas. Para responder, Vela envía la pregunta al modelo de lenguaje de OpenAI y envía términos de búsqueda derivados de ella a PubMed y openFDA. Los registros del servidor de Vela guardan la longitud de la pregunta, no su texto. Para controlar el presupuesto diario, Vela guarda un recuento de uso bajo un identificador generado con un hash unidireccional a partir de tu dirección IP y tu sesión del navegador; el recuento no contiene el texto de ninguna pregunta. Las analíticas de uso registran eventos, como cuántas fuentes se citaron, no el texto que escribes.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q6: 'Tenía una suscripción.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a6: 'Todas las suscripciones han terminado. Para preguntas sobre un pago anterior, escribe a support@an-tho.com.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q7: '¿Está disponible el código?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a7: 'Sí. El código fuente está en GitHub.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
  },
  fr: {
    title: 'Vela est archivé', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q1: 'Qu\'est-ce que Vela aujourd\'hui ?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a1: 'Vela était un outil de recherche médicale multilingue pour les professionnels de santé, développé et exploité de février à octobre 2026. C\'est désormais un projet archivé : ce site est une démo de la seule fonction Recherche et n\'est plus maintenu.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q2: 'Est-ce gratuit ?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a2: 'Oui. Il n\'y a ni compte ni paiement. La démo fonctionne avec un petit budget d\'utilisation quotidien ; elle peut donc s\'interrompre jusqu\'au lendemain une fois ce budget épuisé.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q3: 'Que sont devenus Vérifier et Expliquer ?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a3: 'Les deux ont été retirés lors de l\'archivage de Vela. Leur fonctionnement est décrit sur la page du projet.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q4: 'S\'agit-il d\'un avis médical ?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q5: 'Que deviennent mes questions ?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a5: 'Les questions posées dans la démo ne sont pas enregistrées dans une base de données, et Vela n\'a plus de comptes. Pour répondre, Vela envoie la question au modèle de langage d\'OpenAI et envoie à PubMed et openFDA des termes de recherche qui en sont tirés. Les journaux du serveur de Vela enregistrent la longueur de la question, pas son texte. Pour gérer le budget quotidien, Vela tient un compteur d\'utilisation sous un identifiant obtenu par hachage à sens unique de votre adresse IP et de votre session de navigateur ; ce compteur ne contient aucun texte de question. Les statistiques d\'utilisation enregistrent des événements, comme le nombre de sources citées, et non le texte que vous saisissez.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q6: 'J\'avais un abonnement.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a6: 'Tous les abonnements ont pris fin. Pour toute question sur un paiement passé, écrivez à support@an-tho.com.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q7: 'Le code est-il disponible ?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a7: 'Oui. Le code source est sur GitHub.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
  },
  de: {
    title: 'Vela ist archiviert', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q1: 'Was ist Vela jetzt?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a1: 'Vela war ein mehrsprachiges medizinisches Suchwerkzeug für Fachkräfte im Gesundheitswesen, entwickelt und betrieben von Februar bis Oktober 2026. Es ist jetzt ein archiviertes Projekt: Diese Website ist eine Demo nur der Funktion Recherche und wird nicht mehr gepflegt.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q2: 'Ist es kostenlos?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a2: 'Ja. Es gibt keine Konten und keine Zahlungen. Die Demo läuft mit einem kleinen täglichen Nutzungsbudget und kann daher bis zum nächsten Tag pausieren, wenn das Budget aufgebraucht ist.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q3: 'Was ist mit Prüfen und Erklären passiert?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a3: 'Beide wurden mit der Archivierung von Vela eingestellt. Wie sie funktionierten, ist auf der Projektseite beschrieben.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q4: 'Ist das eine medizinische Beratung?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q5: 'Was passiert mit meinen Fragen?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a5: 'Fragen in der Demo werden nicht in einer Datenbank gespeichert, und Vela hat keine Konten mehr. Um eine Frage zu beantworten, sendet Vela sie an das Sprachmodell von OpenAI und daraus abgeleitete Suchbegriffe an PubMed und openFDA. Die Serverprotokolle von Vela erfassen die Länge einer Frage, nicht ihren Text. Um das Tagesbudget einzuhalten, führt Vela einen Nutzungszähler unter einer Kennung, die per Einweg-Hash aus Ihrer IP-Adresse und Ihrer Browsersitzung gebildet wird; der Zähler enthält keinen Fragetext. Die Nutzungsanalyse erfasst Ereignisse, etwa wie viele Quellen zitiert wurden, nicht den Text, den Sie eingeben.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q6: 'Ich hatte ein Abonnement.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a6: 'Alle Abonnements sind beendet. Bei Fragen zu einer früheren Zahlung schreiben Sie an support@an-tho.com.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q7: 'Ist der Code verfügbar?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a7: 'Ja. Der Quellcode liegt auf GitHub.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
  },
  it: {
    title: 'Vela è archiviato', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q1: 'Che cos\'è Vela oggi?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a1: 'Vela era uno strumento di ricerca medica multilingue per i professionisti sanitari, sviluppato e gestito da febbraio a ottobre 2026. Ora è un progetto archiviato: questo sito è una demo della sola funzione Ricerca e non è più mantenuto.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q2: 'È gratuito?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a2: 'Sì. Non ci sono account né pagamenti. La demo funziona con un piccolo budget di utilizzo giornaliero, quindi può fermarsi fino al giorno dopo una volta esaurito.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q3: 'Che fine hanno fatto Verifica e Spiega?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a3: 'Entrambe sono state ritirate quando Vela è stato archiviato. Il loro funzionamento è descritto nella pagina del progetto.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q4: 'Si tratta di un consiglio medico?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q5: 'Che cosa succede alle mie domande?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a5: 'Le domande poste nella demo non vengono salvate in un database e Vela non ha più account. Per rispondere, Vela invia la domanda al modello linguistico di OpenAI e invia a PubMed e openFDA termini di ricerca ricavati da essa. I log del server di Vela registrano la lunghezza della domanda, non il suo testo. Per gestire il budget giornaliero, Vela tiene un conteggio di utilizzo sotto un identificativo ottenuto con un hash unidirezionale del tuo indirizzo IP e della sessione del browser; il conteggio non contiene alcun testo delle domande. Le analisi di utilizzo registrano eventi, come il numero di fonti citate, non il testo che digiti.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q6: 'Avevo un abbonamento.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a6: 'Tutti gli abbonamenti sono terminati. Per domande su un pagamento passato, scrivi a support@an-tho.com.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q7: 'Il codice è disponibile?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a7: 'Sì. Il codice sorgente è su GitHub.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
  },
  pt: {
    title: 'O Vela foi arquivado', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q1: 'O que é o Vela agora?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a1: 'O Vela foi uma ferramenta de busca médica multilíngue para profissionais de saúde, desenvolvida e operada de fevereiro a outubro de 2026. Agora é um projeto arquivado: este site é uma demonstração apenas da função Pesquisa e não recebe mais manutenção.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q2: 'É gratuito?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a2: 'Sim. Não há contas nem pagamentos. A demonstração funciona com um pequeno orçamento de uso diário, então pode pausar até o dia seguinte quando ele se esgotar.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q3: 'O que aconteceu com Verificar e Explicar?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a3: 'Ambas foram descontinuadas quando o Vela foi arquivado. O funcionamento delas está descrito na página do projeto.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q4: 'Isto é aconselhamento médico?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q5: 'O que acontece com as minhas perguntas?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a5: 'As perguntas feitas na demonstração não são salvas em um banco de dados, e o Vela não tem mais contas. Para responder, o Vela envia a pergunta ao modelo de linguagem da OpenAI e envia termos de busca derivados dela ao PubMed e ao openFDA. Os logs do servidor do Vela registram o tamanho da pergunta, não o seu texto. Para controlar o orçamento diário, o Vela mantém uma contagem de uso sob um identificador gerado por hash unidirecional a partir do seu endereço IP e da sua sessão do navegador; essa contagem não contém nenhum texto de pergunta. As análises de uso registram eventos, como quantas fontes foram citadas, e não o texto que você digita.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q6: 'Eu tinha uma assinatura.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a6: 'Todas as assinaturas foram encerradas. Para dúvidas sobre um pagamento anterior, escreva para support@an-tho.com.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q7: 'O código está disponível?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a7: 'Sim. O código-fonte está no GitHub.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
  },
  th: {
    title: 'Vela ถูกเก็บถาวรแล้ว', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q1: 'ตอนนี้ Vela คืออะไร?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a1: 'Vela เป็นเครื่องมือค้นหาข้อมูลทางการแพทย์หลายภาษาสำหรับบุคลากรทางการแพทย์ พัฒนาและให้บริการตั้งแต่เดือนกุมภาพันธ์ถึงตุลาคม 2026 ปัจจุบันเป็นโปรเจกต์ที่เก็บถาวรแล้ว เว็บไซต์นี้เป็นเดโมที่มีเฉพาะฟังก์ชันวิจัยและไม่มีการดูแลรักษาอีกต่อไป', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q2: 'ใช้ฟรีไหม?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a2: 'ฟรี ไม่มีบัญชีและไม่มีการชำระเงิน เดโมมีงบประมาณการใช้งานรายวันจำนวนจำกัด จึงอาจหยุดชั่วคราวจนถึงวันถัดไปเมื่องบประมาณหมด', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q3: 'ฟังก์ชันตรวจสอบและอธิบายไปไหน?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a3: 'ทั้งสองฟังก์ชันถูกยุติเมื่อ Vela ถูกเก็บถาวร วิธีการทำงานของทั้งสองอธิบายไว้ในหน้าโปรเจกต์', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q4: 'นี่คือคำแนะนำทางการแพทย์หรือไม่?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q5: 'คำถามของฉันจะถูกจัดการอย่างไร?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a5: 'คำถามที่ถามในเดโมจะไม่ถูกบันทึกลงฐานข้อมูล และ Vela ไม่มีบัญชีผู้ใช้อีกต่อไป เพื่อตอบคำถาม Vela จะส่งคำถามไปยังโมเดลภาษาของ OpenAI และส่งคำค้นหาที่สร้างจากคำถามไปยัง PubMed และ openFDA บันทึก (log) ของเซิร์ฟเวอร์ Vela เก็บเพียงความยาวของคำถาม ไม่เก็บข้อความของคำถาม เพื่อควบคุมงบประมาณรายวัน Vela จะนับจำนวนการใช้งานภายใต้รหัสระบุที่สร้างจากที่อยู่ IP และเซสชันเบราว์เซอร์ของคุณด้วยการแฮชทางเดียว โดยตัวนับนี้ไม่มีข้อความคำถามใด ๆ การวิเคราะห์การใช้งานบันทึกเฉพาะเหตุการณ์ เช่น จำนวนแหล่งอ้างอิง ไม่ได้บันทึกข้อความที่คุณพิมพ์', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q6: 'ฉันเคยสมัครสมาชิก', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a6: 'การสมัครสมาชิกทั้งหมดสิ้นสุดแล้ว หากมีคำถามเกี่ยวกับการชำระเงินในอดีต โปรดเขียนถึง support@an-tho.com', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q7: 'มีซอร์สโค้ดให้ดูไหม?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a7: 'มี ซอร์สโค้ดอยู่บน GitHub', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
  },
  ar: {
    title: 'تمت أرشفة Vela', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q1: 'ما هو Vela الآن؟', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a1: 'كان Vela أداة بحث طبي متعددة اللغات للعاملين في الرعاية الصحية، طُوِّرت وشُغِّلت من فبراير إلى أكتوبر 2026. وهو الآن مشروع مؤرشف: هذا الموقع عرض تجريبي لميزة البحث فقط ولم يعد يخضع للصيانة.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q2: 'هل هو مجاني؟', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a2: 'نعم. لا توجد حسابات ولا مدفوعات. يعمل العرض التجريبي بميزانية استخدام يومية صغيرة، لذا قد يتوقف حتى اليوم التالي عند نفادها.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q3: 'ماذا حدث لميزتي التحقق والشرح؟', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a3: 'أُوقفت الميزتان عند أرشفة Vela. وتُوضَّح طريقة عملهما في صفحة المشروع.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q4: 'هل هذه نصيحة طبية؟', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q5: 'ماذا يحدث لأسئلتي؟', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a5: 'لا تُحفظ الأسئلة المطروحة في العرض التجريبي في قاعدة بيانات، ولم يعد لدى Vela حسابات. للإجابة عن سؤال، يرسل Vela السؤال إلى نموذج اللغة من OpenAI ويرسل مصطلحات بحث مشتقة منه إلى PubMed وopenFDA. تسجّل سجلات خادم Vela طول السؤال، لا نصه. وللتحكم في الميزانية اليومية، يحتفظ Vela بعدد مرات الاستخدام تحت معرّف ناتج عن تجزئة أحادية الاتجاه لعنوان IP الخاص بك وجلسة المتصفح، ولا يتضمن هذا العدد أي نص للأسئلة. وتسجّل تحليلات الاستخدام أحداثًا، مثل عدد المصادر المستشهد بها، وليس النص الذي تكتبه.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q6: 'كان لدي اشتراك.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a6: 'انتهت جميع الاشتراكات. للاستفسار عن دفعة سابقة، راسلنا على support@an-tho.com.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q7: 'هل الشيفرة المصدرية متاحة؟', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a7: 'نعم. الشيفرة المصدرية موجودة على GitHub.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
  },
  hi: {
    title: 'Vela संग्रहीत कर दिया गया है', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q1: 'अब Vela क्या है?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a1: 'Vela स्वास्थ्य पेशेवरों के लिए एक बहुभाषी चिकित्सा खोज उपकरण था, जिसे फ़रवरी से अक्टूबर 2026 तक विकसित और संचालित किया गया। अब यह एक संग्रहीत परियोजना है: यह साइट केवल अनुसंधान सुविधा का डेमो है और अब इसका रखरखाव नहीं किया जाता।', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q2: 'क्या यह मुफ़्त है?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a2: 'हाँ। न कोई खाता है, न कोई भुगतान। डेमो एक छोटे दैनिक उपयोग बजट पर चलता है, इसलिए बजट खत्म होने पर यह अगले दिन तक रुक सकता है।', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q3: 'सत्यापित करें और समझाएं सुविधाओं का क्या हुआ?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a3: 'Vela के संग्रहीत होने पर दोनों सुविधाएँ बंद कर दी गईं। वे कैसे काम करती थीं, यह परियोजना पृष्ठ पर बताया गया है।', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q4: 'क्या यह चिकित्सा सलाह है?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q5: 'मेरे प्रश्नों का क्या होता है?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a5: 'डेमो में पूछे गए प्रश्न किसी डेटाबेस में सहेजे नहीं जाते, और Vela में अब खाते नहीं हैं। उत्तर देने के लिए Vela प्रश्न को OpenAI के भाषा मॉडल को भेजता है और उससे बने खोज शब्द PubMed और openFDA को भेजता है। Vela के सर्वर लॉग प्रश्न की लंबाई दर्ज करते हैं, उसका पाठ नहीं। दैनिक बजट लागू करने के लिए Vela आपके IP पते और ब्राउज़र सत्र से एकतरफ़ा हैश द्वारा बने पहचानकर्ता के तहत उपयोग की गिनती रखता है; इस गिनती में किसी प्रश्न का पाठ नहीं होता। उपयोग विश्लेषण केवल घटनाएँ दर्ज करता है, जैसे कितने स्रोत उद्धृत हुए, न कि वह पाठ जो आप लिखते हैं।', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q6: 'मेरी सदस्यता थी।', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a6: 'सभी सदस्यताएँ समाप्त हो चुकी हैं। पिछले भुगतान से जुड़े प्रश्नों के लिए support@an-tho.com पर लिखें।', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q7: 'क्या कोड उपलब्ध है?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a7: 'हाँ। सोर्स कोड GitHub पर है।', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
  },
  bn: {
    title: 'Vela আর্কাইভ করা হয়েছে', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q1: 'Vela এখন কী?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a1: 'Vela ছিল স্বাস্থ্যসেবা পেশাজীবীদের জন্য একটি বহুভাষিক চিকিৎসা অনুসন্ধান টুল, যা ফেব্রুয়ারি থেকে অক্টোবর 2026 পর্যন্ত তৈরি ও পরিচালিত হয়েছে। এটি এখন একটি আর্কাইভ করা প্রকল্প: এই সাইটটি শুধু গবেষণা ফিচারের একটি ডেমো এবং আর রক্ষণাবেক্ষণ করা হয় না।', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q2: 'এটি কি বিনামূল্যে?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a2: 'হ্যাঁ। কোনো অ্যাকাউন্ট নেই, কোনো পেমেন্টও নেই। ডেমোটি একটি ছোট দৈনিক ব্যবহার বাজেটে চলে, তাই বাজেট শেষ হলে পরের দিন পর্যন্ত এটি বন্ধ থাকতে পারে।', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q3: 'যাচাই ও ব্যাখ্যা ফিচারের কী হলো?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a3: 'Vela আর্কাইভ হওয়ার সময় দুটি ফিচারই বন্ধ করা হয়েছে। সেগুলো কীভাবে কাজ করত তা প্রকল্প পৃষ্ঠায় বর্ণনা করা আছে।', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q4: 'এটি কি চিকিৎসা পরামর্শ?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q5: 'আমার প্রশ্নগুলোর কী হয়?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a5: 'ডেমোতে করা প্রশ্ন কোনো ডাটাবেসে সংরক্ষণ করা হয় না, এবং Vela-তে আর কোনো অ্যাকাউন্ট নেই। উত্তর দিতে Vela প্রশ্নটি OpenAI-এর ভাষা মডেলে পাঠায় এবং প্রশ্নের ভিত্তিতে তৈরি অনুসন্ধান শব্দ PubMed ও openFDA-তে পাঠায়। Vela-র সার্ভার লগে প্রশ্নের দৈর্ঘ্য রেকর্ড হয়, প্রশ্নের লেখা নয়। দৈনিক বাজেট নিয়ন্ত্রণে রাখতে Vela আপনার IP ঠিকানা ও ব্রাউজার সেশন থেকে একমুখী হ্যাশের মাধ্যমে তৈরি একটি শনাক্তকারীর অধীনে ব্যবহারের সংখ্যা রাখে; এই সংখ্যায় কোনো প্রশ্নের লেখা থাকে না। ব্যবহার বিশ্লেষণ কেবল ঘটনা রেকর্ড করে, যেমন কতগুলো উৎস উদ্ধৃত হয়েছে, আপনি যা লেখেন তা নয়।', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q6: 'আমার একটি সাবস্ক্রিপশন ছিল।', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a6: 'সব সাবস্ক্রিপশন শেষ হয়ে গেছে। আগের কোনো পেমেন্ট নিয়ে প্রশ্ন থাকলে support@an-tho.com-এ লিখুন।', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q7: 'কোড কি পাওয়া যায়?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a7: 'হ্যাঁ। সোর্স কোড GitHub-এ আছে।', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
  },
  he: {
    title: 'Vela הועבר לארכיון', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q1: 'מה זה Vela עכשיו?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a1: 'Vela היה כלי חיפוש רפואי רב-לשוני לאנשי מקצוע בתחום הבריאות, שפותח והופעל מפברואר עד אוקטובר 2026. כעת זהו פרויקט בארכיון: האתר הזה הוא הדגמה של תכונת המחקר בלבד ואינו מתוחזק עוד.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q2: 'האם זה בחינם?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a2: 'כן. אין חשבונות ואין תשלומים. ההדגמה פועלת בתקציב שימוש יומי קטן, ולכן ייתכן שתיעצר עד למחרת כשהתקציב ינוצל.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q3: 'מה קרה לתכונות האימות וההסבר?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a3: 'שתיהן הופסקו כשהפרויקט הועבר לארכיון. אופן פעולתן מתואר בדף הפרויקט.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q4: 'האם זו עצה רפואית?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q5: 'מה קורה לשאלות שלי?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a5: 'שאלות שנשאלות בהדגמה אינן נשמרות במסד נתונים, ול-Vela כבר אין חשבונות. כדי לענות, Vela שולח את השאלה למודל השפה של OpenAI ושולח מונחי חיפוש הנגזרים ממנה ל-PubMed ול-openFDA. יומני השרת של Vela מתעדים את אורך השאלה, לא את הטקסט שלה. כדי לאכוף את התקציב היומי, Vela שומר ספירת שימוש תחת מזהה שנוצר בגיבוב חד-כיווני מכתובת ה-IP שלך ומהפעלת הדפדפן; הספירה אינה כוללת טקסט של שאלות. ניתוח השימוש מתעד אירועים, כמו מספר המקורות שצוטטו, ולא את הטקסט שאתה מקליד.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q6: 'היה לי מנוי.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a6: 'כל המנויים הסתיימו. לשאלות על תשלום קודם, כתבו אל support@an-tho.com.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q7: 'האם הקוד זמין?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a7: 'כן. קוד המקור נמצא ב-GitHub.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
  },
  vi: {
    title: 'Vela đã được lưu trữ', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q1: 'Vela bây giờ là gì?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a1: 'Vela từng là công cụ tìm kiếm y khoa đa ngôn ngữ dành cho nhân viên y tế, được phát triển và vận hành từ tháng 2 đến tháng 10 năm 2026. Giờ đây đây là một dự án đã được lưu trữ: trang này chỉ là bản demo của tính năng Nghiên cứu và không còn được bảo trì.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q2: 'Có miễn phí không?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a2: 'Có. Không có tài khoản và không có thanh toán. Bản demo chạy với ngân sách sử dụng hằng ngày nhỏ, nên có thể tạm dừng đến hôm sau khi hết ngân sách.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q3: 'Xác minh và Giải thích đã đi đâu?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a3: 'Cả hai đã ngừng hoạt động khi Vela được lưu trữ. Cách chúng hoạt động được mô tả trên trang dự án.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q4: 'Đây có phải là lời khuyên y tế không?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q5: 'Câu hỏi của tôi được xử lý thế nào?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a5: 'Các câu hỏi trong bản demo không được lưu vào cơ sở dữ liệu, và Vela không còn tài khoản. Để trả lời, Vela gửi câu hỏi đến mô hình ngôn ngữ của OpenAI và gửi các từ khóa tìm kiếm rút ra từ câu hỏi đến PubMed và openFDA. Nhật ký máy chủ của Vela chỉ ghi lại độ dài của câu hỏi, không ghi nội dung. Để kiểm soát ngân sách hằng ngày, Vela đếm số lượt sử dụng theo một mã định danh được tạo bằng hàm băm một chiều từ địa chỉ IP và phiên trình duyệt của bạn; số đếm này không chứa nội dung câu hỏi nào. Phân tích sử dụng chỉ ghi lại sự kiện, chẳng hạn số nguồn được trích dẫn, không ghi lại nội dung bạn nhập.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q6: 'Tôi từng có gói đăng ký.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a6: 'Tất cả gói đăng ký đã kết thúc. Nếu có câu hỏi về khoản thanh toán trước đây, vui lòng viết thư đến support@an-tho.com.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    q7: 'Mã nguồn có sẵn không?', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
    a7: 'Có. Mã nguồn có trên GitHub.', // MACHINE-TRANSLATED 2026-10-05 — archive UI car
  },
};
