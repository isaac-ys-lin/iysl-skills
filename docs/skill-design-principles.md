# Skill design principles

這份文件是 repository maintainer 的設計邊界。它描述 skill 應保留什麼判斷
與驗證，不是要求模型照抄的固定 SOP。

## 1. 先定義成果

- Skill 的第一責任是說清楚使用者要得到的結果。
- Description 同時說明適用情境與主要排除，避免只靠名稱觸發。
- Acceptance criteria 應描述可觀察結果、可交付 artifact 或驗證證據。
- 未指定的可逆選擇由執行 agent 依 repo convention、成本與風險自行決定。

## 2. 主檔只放 load-bearing context

主 `SKILL.md` 優先保留五類資訊：

1. **Intent**：要完成的成果與使用者意向。
2. **Use and boundaries**：何時使用、何時交給相鄰 workflow。
3. **Invariants**：來源、權限、安全、資料或相容性不可破壞的邊界。
4. **Adaptive execution**：先走最簡單可成功路徑，必要時才升級。
5. **Validation and resources**：必須通過的驗證器，以及何時讀 reference。

不要把一般模型能力重新教一遍。除非已有可重現的領域失敗模式，否則不把
「要專業」「要有邏輯」「要檢查結果」寫成永久規則。

## 3. AI 擁有可逆決策

模型可以自行選擇命名、內部結構、一般工具、layout、候選數量、分工與修訂
順序。Skill 只有在自由度已被證明會穩定造成重大錯誤時，才應限制這些選擇。

使用者明確要求 variants、深入審查或高價值外部交付時，可以增加候選、agent
或 review。這些是 adaptive escalation，不是每次任務的 ceremony。

## 4. Deterministic 規則交給程式

- 必要欄位、固定檔名與 section schema 用 validator 或 test 保護。
- path safety、secret scan、artifact existence、HTML/SVG parse 與 package
  inventory 不靠模型自行宣稱。
- Validator 應回報可修復的具體失敗，不以主檔複述全部 assertion。
- AI judge 可補充品質評估，但不能取代必要的 deterministic release gate。

## 5. References 按需載入

Reference 應保存特殊領域知識、相容模式、troubleshooting、品質 calibration
或 optional escalation。主檔只說明什麼情況要讀它；同一規則應只有一個 authority。

Examples 是 calibration，不是每個任務都必須複製的 template。相容性與失敗處理
可以保留，但不要讓罕見 fallback 膨脹成所有任務都必須走的流程。

## 6. Adaptive execution

預設路徑是：讀取必要 context，採最小成功方案，執行 validator，針對失敗項
修復，達成 acceptance 後停止。只有品質不足、風險高、不確定性高、工具缺失或
使用者明確要求時，才增加探索、候選、subagent 或 review 深度。

簡單完整案例不應因 skill 存在而增加問題、agent calls 或 tool calls。若行為
需要詢問，問題必須對應 material intent、權限、不可逆效果或相容性取捨。

## 7. 維護與驗證

- 先用 `tools/audit-skills.py` 檢查 package shape、資源連結與 runtime 說明。
- 再跑現有 per-skill tests、release inventory 與 isolated install parity。
- 新增可 deterministic 判定的規則時，優先加入 test/schema/validator。
- 新增主檔規則時，同時加入能重現該失敗模式的 behavior eval。
- 不能用行數變少本身宣稱精簡成功；要比較 routing、品質、成本與退步案例。

這些原則不改變 MIT License、安裝方式、現有 release contract 或各 skill 的
領域安全邊界。
