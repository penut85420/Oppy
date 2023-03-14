# 歐派勞工 Oppy Discord Bot

歐派勞工 Oppy 是一個串接 ChatGPT 的 Discord 機器人，並且套上簡繁轉換的套件。

## 使用說明

1. 安裝相關套件：
    + `pip install -r requirements.txt`
2. 根據 `Config.Template.json` 建立自己的設定檔。
3. 執行 `OppyBot.py` 啟動機器人：
    + e.g. `python OppyBot.py Config.json`

## 設定檔說明

+ `api_key` 設定 OpenAI API 金鑰。
+ `discord_token` 設定 Discord Bot Token。
+ `target_channels` 設定接收聊天訊息的頻道。
+ `command_prefix` 設定相關指令的前綴。
+ `converter_type` 簡繁轉換的種類，請參考 [OpenCC](https://github.com/BYVoid/OpenCC) 專案。
+ `delim` 遇到哪些標點符號時會更新訊息。
+ `emoji_done` 當完成訊息回覆時，要加上的表情符號反應。
+ `emoji_pending` 當訊息正在回覆時，要加上的表情符號反應。
+ `reset_command` 重置聊天的指令名稱。
+ `help_command` 幫助訊息的指令名稱。
+ `help_message` 幫助訊息的格式化字串，此字串會代入四個字串，使用 `%s` 表示。
+ `message_no_resp` 當 API 發生錯誤而無法取得回應時，要回覆給使用者的訊息。
+ `message_on_error` 當產生回覆的過程中發生錯誤時，要回覆給使用者的訊息。
+ `message_reset` 當重置聊天訊息時，要回覆給使用者的訊息。
+ `message_waiting` 當機器人準備開始回覆之前，要先發送的前置訊息。
+ `reset_delta` 設定間隔多久沒傳送訊息時，會自動重置聊天。
+ `system_prompt` 設定機器人的初始 Prompt，例如人設之類的。
+ `max_turns` 設定最多幾輪對話會重置訊息。
