#!/bin/bash
# Quick database queries for Taraji AI

DB="data/taraji_ai.db"

echo "=========================================="
echo "DATABASE QUERIES FOR TARAJI AI"
echo "=========================================="
echo ""

# 1. Count total articles
echo "1. Total articles in database:"
sqlite3 $DB "SELECT COUNT(*) FROM articles;"
echo ""

# 2. Recent articles with titles
echo "2. Last 10 articles (titles only):"
sqlite3 $DB "SELECT id, title, source FROM articles ORDER BY id DESC LIMIT 10;"
echo ""

# 3. Articles with summaries
echo "3. Articles with summaries (last 5):"
sqlite3 $DB "SELECT id, title, substr(summary, 1, 100) || '...' as summary FROM articles WHERE length(summary) > 50 ORDER BY id DESC LIMIT 5;"
echo ""

# 4. Count by source
echo "4. Articles by source:"
sqlite3 $DB "SELECT source, COUNT(*) as count FROM articles GROUP BY source ORDER BY count DESC;"
echo ""

# 5. Count by language
echo "5. Articles by language:"
sqlite3 $DB "SELECT language, COUNT(*) as count FROM articles GROUP BY language ORDER BY count DESC;"
echo ""

# 6. Count by category
echo "6. Articles by category:"
sqlite3 $DB "SELECT category, COUNT(*) as count FROM articles GROUP BY category ORDER BY count DESC;"
echo ""

# 7. Check matched keywords
echo "7. Sample of matched keywords:"
sqlite3 $DB "SELECT a.id, a.title, k.keyword, k.match_type FROM articles a LEFT JOIN keywords_matched k ON a.id = k.article_id ORDER BY a.id DESC LIMIT 10;"
echo ""

echo "=========================================="
