/**
 * Google Apps Script — 貼上文字自動新增 Google Calendar 活動
 * 使用 Claude API 解析自然語言，透過 CalendarApp 建立事件
 */

function doGet() {
  return HtmlService.createHtmlOutputFromFile('index')
    .setTitle('新增行事曆活動')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

/**
 * 由前端呼叫：解析文字並建立行事曆事件
 * @param {string} text 使用者貼入的活動描述文字
 * @returns {Object} { success, title, start, end, location, description, error }
 */
function parseAndCreateEvent(text) {
  if (!text || text.trim() === '') {
    return { success: false, error: '請輸入活動描述文字。' };
  }

  var apiKey = PropertiesService.getScriptProperties().getProperty('ANTHROPIC_API_KEY');
  if (!apiKey) {
    return { success: false, error: '尚未設定 ANTHROPIC_API_KEY，請參考說明文件完成設定。' };
  }

  // 注入今天的日期（台北時區），讓 Claude 能正確解析「明天」「下週」等相對日期
  var today = Utilities.formatDate(new Date(), 'Asia/Taipei', 'yyyy-MM-dd');
  var dayOfWeek = Utilities.formatDate(new Date(), 'Asia/Taipei', 'EEEE');

  var systemPrompt = [
    '今天日期：' + today + '（' + dayOfWeek + '，Asia/Taipei，UTC+8）。',
    '你是一個行事曆助理，請將使用者描述的活動解析成 JSON。',
    '規則：',
    '- 只回傳純 JSON，不加任何說明文字、不加 markdown 程式碼區塊。',
    '- start 和 end 格式：yyyy-MM-ddTHH:mm:ss（24 小時制）。',
    '- 若未提及結束時間，預設 end = start + 1 小時。',
    '- 若提到「約 N 小時/分鐘」，依此計算 end。',
    '- 模糊日期（如「明天」「下週五」「5/1」）取最近的未來日期；年份未指定預設今年，若今年已過則取明年。',
    '- location 和 description 若無則設為 null。',
    '- 若無法判斷具體日期或時間，將 error 填入缺少的資訊說明（繁體中文），其餘欄位可為 null。',
    '- 若資訊完整，error 設為 null。',
    '',
    '回傳格式（嚴格遵守）：',
    '{',
    '  "title": "活動名稱",',
    '  "start": "2025-05-01T14:00:00",',
    '  "end": "2025-05-01T15:00:00",',
    '  "location": "地點或 null",',
    '  "description": "備註或 null",',
    '  "error": null',
    '}'
  ].join('\n');

  var payload = {
    model: 'claude-sonnet-4-6',
    max_tokens: 512,
    system: systemPrompt,
    messages: [{ role: 'user', content: text.trim() }]
  };

  var options = {
    method: 'post',
    contentType: 'application/json',
    headers: {
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01'
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };

  var response;
  try {
    response = UrlFetchApp.fetch('https://api.anthropic.com/v1/messages', options);
  } catch (e) {
    return { success: false, error: '無法連線到 Claude API：' + e.message };
  }

  var statusCode = response.getResponseCode();
  if (statusCode !== 200) {
    return { success: false, error: 'Claude API 回傳錯誤（HTTP ' + statusCode + '）。請確認 API Key 是否正確。' };
  }

  var responseJson;
  try {
    responseJson = JSON.parse(response.getContentText());
  } catch (e) {
    return { success: false, error: '無法解析 Claude API 回應。' };
  }

  var rawText = responseJson.content && responseJson.content[0] && responseJson.content[0].text;
  if (!rawText) {
    return { success: false, error: 'Claude API 回應格式不符預期。' };
  }

  // 移除可能的 markdown 程式碼區塊包裝
  var cleaned = rawText.trim().replace(/^```(?:json)?\n?/, '').replace(/\n?```$/, '').trim();

  var parsed;
  try {
    parsed = JSON.parse(cleaned);
  } catch (e) {
    return { success: false, error: '無法解析活動資訊，請嘗試更清楚地描述活動時間。' };
  }

  if (parsed.error) {
    return { success: false, error: '資訊不足：' + parsed.error };
  }

  if (!parsed.title || !parsed.start || !parsed.end) {
    return { success: false, error: '無法從描述中取得完整的活動資訊（需要標題、開始與結束時間）。' };
  }

  var startDate, endDate;
  try {
    // Apps Script 的 new Date() 接受 ISO 8601 字串，但需補上時區偏移
    startDate = new Date(parsed.start + '+08:00');
    endDate = new Date(parsed.end + '+08:00');
  } catch (e) {
    return { success: false, error: '日期時間格式錯誤：' + e.message };
  }

  if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) {
    return { success: false, error: '解析到的日期時間無效，請重新描述。' };
  }

  var calendar = CalendarApp.getDefaultCalendar();
  var eventOptions = {};
  if (parsed.location) eventOptions.location = parsed.location;
  if (parsed.description) eventOptions.description = parsed.description;

  var event;
  try {
    event = calendar.createEvent(parsed.title, startDate, endDate, eventOptions);
  } catch (e) {
    return { success: false, error: '建立行事曆事件失敗：' + e.message };
  }

  // 格式化顯示用的時間字串（台北時區）
  var displayStart = Utilities.formatDate(startDate, 'Asia/Taipei', 'yyyy/MM/dd HH:mm');
  var displayEnd = Utilities.formatDate(endDate, 'Asia/Taipei', 'HH:mm');

  return {
    success: true,
    title: parsed.title,
    start: displayStart,
    end: displayEnd,
    location: parsed.location || null,
    description: parsed.description || null,
    calendarName: calendar.getName()
  };
}
