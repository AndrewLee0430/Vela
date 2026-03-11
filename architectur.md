```
graph TD
    %% 樣式定義
    classDef research fill:#ff8e6e22,stroke:#ff8e6e,stroke-width:2px,color:#ff8e6e
    classDef verify fill:#63b3ed22,stroke:#63b3ed,stroke-width:2px,color:#63b3ed
    classDef explain fill:#68d39122,stroke:#68d391,stroke-width:2px,color:#68d391
    classDef guard fill:#fc818122,stroke:#fc8181,stroke-width:2px,color:#fc8181
    classDef infra fill:#b794f422,stroke:#b794f4,stroke-width:2px,color:#b794f4
    classDef db fill:#f6e05e22,stroke:#f6e05e,stroke-width:2px,color:#f6e05e
    classDef ext fill:#76e4f722,stroke:#76e4f7,stroke-width:2px,color:#76e4f7

    %% 流程內容
    User([User]) -- HTTPS --&gt; FE[Next.js 14 Frontend]
    FE -- REST / SSE --&gt; Auth[Clerk JWT Auth]
    Auth --&gt; API[FastAPI Backend]

    subgraph Guards [🛡️ INPUT GUARDS]
        G0[0. Length Check] --&gt; G1[1. PHI Regex]
        G1 --&gt; G2[2. Injection Check]
        G2 --&gt; G3[3. Intent GPT-4-mini]
        G3 --&gt; G4[4. Rate Limit]
    end
    
    API --&gt; G0
    G4 -- Passed --&gt; Router{Pipeline Router}

    subgraph RP [🔍 RESEARCH PIPELINE]
        R1[Query Rewriting] --&gt; R_Data{Data Retrieval}
        R_Data --&gt; R_DB[(Chroma DB)]
        R_Data --&gt; R_Pub[PubMed API]
        R_Data --&gt; R_FDA[FDA API]
        R_DB &amp; R_Pub &amp; R_FDA --&gt; R2[Dedup + Year Boost]
        R2 --&gt; R3[LLM-as-Judge]
        R3 --&gt; R4[Reranker top_k=8]
        R4 --&gt; R5[GPT-4.1 Generator]
    end

    subgraph VP [✅ VERIFY PIPELINE]
        V1[Drug Name Parser] --&gt; V2[Levenshtein Correction]
        V2 --&gt; V3[FDA Cache Check]
        V3 -- miss --&gt; V4[OpenFDA Live API]
        V4 &amp; V3 --&gt; V5[GPT-4 Interaction Analysis]
        V5 --&gt; V6[Structured Response]
    end

    Router --&gt; RP
    Router --&gt; VP

    %% 套用顏色
    class G0,G1,G2,G3,G4 guard
    class R1,R2,R3,R4,R5 research
    class V1,V2,V5,V6 verify
    class Auth infra
    class R_DB,V3 db
    class R_Pub,R_FDA,V4 ext
```
