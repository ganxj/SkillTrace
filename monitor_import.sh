#!/bin/bash
# 监控指定导入任务的生成状态

API_BASE="http://localhost:8001/api/v1"
IMPORT_ID="${1:-66c457cd-3ce0-44e6-9823-0447ab355517}"

echo "================================================"
echo "📊 监控课程生成进度"
echo "================================================"
echo "Import ID: $IMPORT_ID"
echo ""

TIMEOUT=1200
START_TIME=$(date +%s)
LAST_STATUS=""
LAST_STEP=""
LAST_PROCESSED=0

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

  if [ -z "$STATUS_RESPONSE" ]; then
    echo "❌ 无法获取状态"
    sleep 3
    continue
  fi

  STATUS=$(echo "$STATUS_RESPONSE" | grep -o '"status":"[^"]*"' | head -1 | cut -d'"' -f4)
  CURRENT_STEP=$(echo "$STATUS_RESPONSE" | grep -o '"current_step":"[^"]*"' | cut -d'"' -f4)
  TOTAL=$(echo "$STATUS_RESPONSE" | grep -o '"total_segments":[0-9]*' | cut -d':' -f2)
  PROCESSED=$(echo "$STATUS_RESPONSE" | grep -o '"processed_segments":[0-9]*' | cut -d':' -f2)

  # 计算进度百分比
  if [ -n "$TOTAL" ] && [ "$TOTAL" != "0" ] && [ -n "$PROCESSED" ]; then
    PERCENT=$((PROCESSED * 100 / TOTAL))
  else
    PERCENT=0
  fi

  # 在状态变化或进度更新时打印
  if [ "$STATUS" != "$LAST_STATUS" ] || [ "$CURRENT_STEP" != "$LAST_STEP" ] || [ "$PROCESSED" != "$LAST_PROCESSED" ]; then
    TIMESTAMP=$(date +%H:%M:%S)
    PROGRESS=""
    if [ -n "$TOTAL" ] && [ "$TOTAL" != "0" ]; then
      PROGRESS=" [$PROCESSED/$TOTAL - $PERCENT%]"
    fi
    printf "[%s] 状态: %-12s | %s%s\n" "$TIMESTAMP" "$STATUS" "$CURRENT_STEP" "$PROGRESS"
    LAST_STATUS="$STATUS"
    LAST_STEP="$CURRENT_STEP"
    LAST_PROCESSED="$PROCESSED"
  fi

  # 检查终止状态
  if [ "$STATUS" = "published" ]; then
    echo "================================================"
    echo "✅ 课程生成成功！"
    DOMAIN_NAME=$(echo "$STATUS_RESPONSE" | grep -o '"name":"[^"]*"' | head -2 | tail -1 | cut -d'"' -f4)
    DOMAIN_SLUG=$(echo "$STATUS_RESPONSE" | grep -o '"slug":"[^"]*"' | head -2 | tail -1 | cut -d'"' -f4)
    DOMAIN_ID=$(echo "$STATUS_RESPONSE" | grep -o '"id":"[^"]*"' | head -2 | tail -1 | cut -d'"' -f4)
    echo "   课程ID: $DOMAIN_ID"
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

    # 输出完整响应用于调试
    echo ""
    echo "完整响应："
    echo "$STATUS_RESPONSE" | python -m json.tool 2>/dev/null || echo "$STATUS_RESPONSE"
    exit 1
  fi

  sleep 3
done
