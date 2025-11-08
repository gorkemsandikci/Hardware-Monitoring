#!/bin/bash
# GitHub'a yükleme öncesi hazırlık scripti

echo "=== GitHub Hazırlık Kontrolü ==="
echo ""

# 1. Gereksiz dosyaları temizle
echo "1. Gereksiz dosyaları temizliyorum..."
find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "inventory_*.json" -delete 2>/dev/null || true
echo "   ✓ Temizlik tamamlandı"

# 2. Git durumunu kontrol et
echo ""
echo "2. Git durumunu kontrol ediyorum..."
if [ -d ".git" ]; then
    echo "   ✓ Git repository zaten başlatılmış"
    git status --short | head -5
else
    echo "   ⚠ Git repository henüz başlatılmamış"
    echo "   Şu komutları çalıştırın:"
    echo "   git init"
    echo "   git add ."
    echo "   git commit -m 'Initial commit: Hardware Monitor System v1.0.0'"
fi

# 3. Gerekli dosyaları kontrol et
echo ""
echo "3. Gerekli dosyaları kontrol ediyorum..."
files=("README.md" "LICENSE" "CONTRIBUTING.md" ".gitignore" "requirements.txt")
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "   ✓ $file"
    else
        echo "   ✗ $file EKSIK!"
    fi
done

# 4. GitHub klasörlerini kontrol et
echo ""
echo "4. GitHub klasörlerini kontrol ediyorum..."
if [ -d ".github/workflows" ]; then
    echo "   ✓ .github/workflows/ mevcut"
else
    echo "   ✗ .github/workflows/ EKSIK!"
fi

if [ -d ".github/ISSUE_TEMPLATE" ]; then
    echo "   ✓ .github/ISSUE_TEMPLATE/ mevcut"
else
    echo "   ✗ .github/ISSUE_TEMPLATE/ EKSIK!"
fi

echo ""
echo "=== Hazırlık Tamamlandı ==="
echo ""
echo "Sonraki adımlar için GITHUB_SETUP.md dosyasını okuyun."
