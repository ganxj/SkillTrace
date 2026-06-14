#!/bin/bash
# 测试优化后的课程生成性能

API_BASE="http://localhost:8001/api/v1"
PDF_PATH="/d/360极速浏览器X下载/《指数基金   投资指南》.pdf"

echo "================================================"
echo "🚀 测试优化后的课程生成"
echo "================================================"
echo "优化内容: MAX_SEGMENT_CHARS 1800 → 3600"
echo "预期效果: 段数减少约50%，生成时间缩短一半"
echo ""

# 检查文件是否存在
if [ ! -f "$PDF_PATH" ]; then
    echo "❌ PDF文件不存在: $PDF_PATH"
    exit 1
fi

echo "📤 正在上传文件..."
UPLOAD_RESPONSE=$(curl -s -X POST "$API_BASE/imports" -F "file=@$PDF_PATH")

if [ $? -ne 0 ]; then
    echo "❌ 上传失败"
    exit 1
fi

echo "上传响应:"
echo "$UPLOAD_RESPONSE" | head -200

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
echo "📊 监控生成进度（关注 total_segments 数量）"
echo "================================================"

# 等待一下让服务器开始处理
sleep 3

# 获取初始状态查看分段数
STATUS_RESPONSE=$(curl -s "$API_BASE/imports/$IMPORT_ID")
TOTAL=$(echo "$STATUS_RESPONSE" | grep -o '"total_segments":[0-9]*' | cut -d':' -f2)

echo ""
echo "🎯 关键指标:"
echo "   旧版本段数: 113 段"
echo "   本次段数: ${TOTAL:-解析中...} 段"
if [ -n "$TOTAL" ] && [ "$TOTAL" -lt 113 ]; then
    REDUCTION=$(( (113 - TOTAL) * 100 / 113 ))
    echo "   ✅ 优化效果: 减少 ${REDUCTION}%"
else
    echo "   ⏳ 等待分段完成..."
fi
echo ""

# 继续监控
TIMEOUT=3600
START_TIME=$(date +%s)
LAST_PROCESSED=0

while true; do
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))
    if [ $ELAPSED -gt $TIMEOUT ]; then
        echo "⏱️  监控超时 (${TIMEOUT}秒)"
        break
    fi

    STATUS_RESPONSE=$(curl -s "$API_BASE/imports/$IMPORT_ID")
    STATUS=$(echo "$STATUS_RESPONSE" | grep -o '"status":"[^"]*"' | head -1 | cut -d'"' -f4)
    CURRENT_STEP=$(echo "$STATUS_RESPONSE" | grep -o '"current_step":"[^"]*"' | cut -d'"' -f4)
    TOTAL=$(echo "$STATUS_RESPONSE" | grep -o '"total_segments":[0-9]*' | cut -d':' -f2)
    PROCESSED=$(echo "$STATUS_RESPONSE" | grep -o '"processed_segments":[0-9]*' | cut -d':' -f2)

    if [ -n "$TOTAL" ] && [ "$TOTAL" != "0" ] && [ -n "$PROCESSED" ]; then
        PERCENT=$((PROCESSED * 100 / TOTAL))
    else
        PERCENT=0
    fi

    if [ "$PROCESSED" != "$LAST_PROCESSED" ]; then
        TIMESTAMP=$(date +%H:%M:%S)
        PROGRESS=""
        if [ -n "$TOTAL" ] && [ "$TOTAL" != "0" ]; then
            PROGRESS=" [$PROCESSED/$TOTAL - $PERCENT%]"
        fi
        printf "[%s] %s%s\n" "$TIMESTAMP" "$CURRENT_STEP" "$PROGRESS"
        LAST_PROCESSED="$PROCESSED"
    fi

    if [ "$STATUS" = "published" ]; then
        echo "================================================"
        echo "✅ 课程生成成功！"
        DOMAIN_NAME=$(echo "$STATUS_RESPONSE" | grep -o '"name":"[^"]*"' | head -2 | tail -1 | cut -d'"' -f4)
        echo "   课程名称: $DOMAIN_NAME"
        echo "   总段数: $TOTAL"
        echo "   总耗时: ${ELAPSED}秒 ($(($ELAPSED / 60))分钟)"
        if [ -n "$TOTAL" ] && [ "$TOTAL" -gt 0 ]; then
            AVG=$((ELAPSED / TOTAL))
            echo "   平均速度: ${AVG}秒/段"
        fi
        echo "================================================"
        exit 0
    elif [ "$STATUS" = "failed" ]; then
        echo "================================================"
        echo "❌ 课程生成失败！"
        ERROR=$(echo "$STATUS_RESPONSE" | grep -o '"error":"[^"]*"' | cut -d'"' -f4)
        echo "   错误信息: $ERROR"
        echo "================================================"
        exit 1
    fi

    sleep 3
done
