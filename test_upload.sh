#!/bin/bash
# 测试课程生成：上传PDF并监控状态

API_BASE="http://localhost:8001/api/v1"
PDF_PATH="D:\360极速浏览器X下载\《指数基金   投资指南》.pdf"

echo "================================================"
echo "📤 课程生成测试"
echo "================================================"

# 1. 上传文件
echo ""
echo "正在上传文件: $PDF_PATH"
UPLOAD_RESPONSE=$(curl -s -X POST "$API_BASE/imports" \
  -F "file=@$PDF_PATH")

echo "上传响应:"
echo "$UPLOAD_RESPONSE" | python -m json.tool 2>/dev/null || echo "$UPLOAD_RESPONSE"

# 提取 import_id
IMPORT_ID=$(echo "$UPLOAD_RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

if [ -z "$IMPORT_ID" ]; then
  echo ""
  echo "❌ 上传失败，无法获取 import_id"
  exit 1
fi

echo ""
echo "✅ 上传成功！Import ID: $IMPORT_ID"
echo ""
echo "================================================"
echo "📊 监控生成进度"
echo "================================================"

# 2. 监控进度
TIMEOUT=600
START_TIME=$(date +%s)
LAST_STATUS=""
LAST_STEP=""

while true; do
  # 检查超时
  CURRENT_TIME=$(date +%s)
  ELAPSED=$((CURRENT_TIME - START_TIME))
  if [ $ELAPSED -gt $TIMEOUT ]; then
    echo ""
    echo "⏱️  监控超时 (${TIMEOUT}秒)"
    break
  fi

  # 获取状态
  STATUS_RESPONSE=$(curl -s "$API_BASE/imports/$IMPORT_ID")

  STATUS=$(echo "$STATUS_RESPONSE" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
  CURRENT_STEP=$(echo "$STATUS_RESPONSE" | grep -o '"current_step":"[^"]*"' | cut -d'"' -f4)
  TOTAL=$(echo "$STATUS_RESPONSE" | grep -o '"total_segments":[0-9]*' | cut -d':' -f2)
  PROCESSED=$(echo "$STATUS_RESPONSE" | grep -o '"processed_segments":[0-9]*' | cut -d':' -f2)

  # 只在状态变化时打印
  if [ "$STATUS" != "$LAST_STATUS" ] || [ "$CURRENT_STEP" != "$LAST_STEP" ]; then
    TIMESTAMP=$(date +%H:%M:%S)
    PROGRESS=""
    if [ -n "$TOTAL" ] && [ "$TOTAL" != "0" ]; then
      PROGRESS=" [$PROCESSED/$TOTAL]"
    fi
    printf "[%s] 状态: %-12s | %s%s\n" "$TIMESTAMP" "$STATUS" "$CURRENT_STEP" "$PROGRESS"
    LAST_STATUS="$STATUS"
    LAST_STEP="$CURRENT_STEP"
  fi

  # 检查终止状态
  if [ "$STATUS" = "published" ]; then
    echo "================================================"
    echo "✅ 课程生成成功！"
    DOMAIN_NAME=$(echo "$STATUS_RESPONSE" | grep -o '"name":"[^"]*"' | head -1 | cut -d'"' -f4)
    DOMAIN_SLUG=$(echo "$STATUS_RESPONSE" | grep -o '"slug":"[^"]*"' | head -1 | cut -d'"' -f4)
    echo "   课程名称: $DOMAIN_NAME"
    echo "   课程slug: $DOMAIN_SLUG"
    echo "   总耗时: ${ELAPSED}秒"
    echo "================================================"
    exit 0
  elif [ "$STATUS" = "failed" ]; then
    echo "================================================"
    echo "❌ 课程生成失败！"
    ERROR=$(echo "$STATUS_RESPONSE" | grep -o '"error":"[^"]*"' | cut -d'"' -f4)
    echo "   错误信息: $ERROR"
    echo "   当前步骤: $CURRENT_STEP"
    echo "================================================"
    exit 1
  fi

  sleep 2
done
