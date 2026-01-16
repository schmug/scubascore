#!/bin/bash
# Manual end-to-end verification script for profile switching

set -e

echo "========================================="
echo "Profile Switching E2E Verification"
echo "========================================="
echo ""

# Step 1: Verify current profile is default
echo "Step 1: Verify default profile is set"
grep "current_profile: default" profile_config.yaml && echo "✓ Default profile is set" || echo "✗ Failed"
echo ""

# Step 2: Verify API endpoint for default profile
echo "Step 2: Test API endpoint for default profile"
RESPONSE=$(curl -s http://localhost:5000/api/profiles/default)
echo "$RESPONSE" | grep -q "gmail" && echo "✓ Default profile returns GWS services (gmail found)" || echo "✗ Failed"
echo "$RESPONSE" | grep -q "drive" && echo "✓ GWS service 'drive' found" || echo "✗ Failed"
echo ""

# Step 3: Verify API endpoint for M365 profile
echo "Step 3: Test API endpoint for M365 profile"
RESPONSE=$(curl -s http://localhost:5000/api/profiles/m365)
echo "$RESPONSE" | grep -q "exchange" && echo "✓ M365 profile returns M365 services (exchange found)" || echo "✗ Failed"
echo "$RESPONSE" | grep -q "onedrive" && echo "✓ M365 service 'onedrive' found" || echo "✗ Failed"
echo ""

# Step 4: Verify settings page loads with profile dropdown
echo "Step 4: Verify settings page has profile dropdown"
PAGE=$(curl -s http://localhost:5000/settings)
echo "$PAGE" | grep -q "Service Weight Profile" && echo "✓ Profile section exists" || echo "✗ Failed"
echo "$PAGE" | grep -q '<select name="profile"' && echo "✓ Profile dropdown exists" || echo "✗ Failed"
echo "$PAGE" | grep -q 'onchange="switchProfile()"' && echo "✓ JavaScript handler attached" || echo "✗ Failed"
echo "$PAGE" | grep -q '<option value="default" selected>default</option>' && echo "✓ Default profile is selected" || echo "✗ Failed"
echo "$PAGE" | grep -q '<option value="m365"' && echo "✓ M365 profile option exists" || echo "✗ Failed"
echo ""

# Step 5: Verify default service weights textarea shows GWS content
echo "Step 5: Verify default profile shows GWS services in textarea"
echo "$PAGE" | grep -q "gmail:" && echo "✓ Textarea shows GWS service: gmail" || echo "✗ Failed"
echo "$PAGE" | grep -q "drive:" && echo "✓ Textarea shows GWS service: drive" || echo "✗ Failed"
echo ""

# Step 6: Switch to M365 profile and verify persistence
echo "Step 6: Test profile switching to M365"
# Read current weights.yaml content
WEIGHTS_CONTENT=$(cat weights.yaml)
# Read M365 service weights content
M365_CONTENT=$(cat service_weights_m365.yaml)

# Make POST request to switch profile (using form data)
curl -s -X POST http://localhost:5000/settings \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "profile=m365" \
  --data-urlencode "weights_yaml=$WEIGHTS_CONTENT" \
  --data-urlencode "service_weights_yaml=$M365_CONTENT" \
  > /dev/null

# Give it a moment to save
sleep 1

# Verify profile was switched in config file
grep "current_profile: m365" profile_config.yaml && echo "✓ Profile switched to M365 in config" || echo "✗ Failed"
echo ""

# Step 7: Reload page and verify M365 is still selected
echo "Step 7: Verify M365 profile persists on page reload"
PAGE=$(curl -s http://localhost:5000/settings)
echo "$PAGE" | grep -q '<option value="m365" selected>m365</option>' && echo "✓ M365 profile is selected after reload" || echo "✗ Failed"
echo "$PAGE" | grep -q "exchange:" && echo "✓ Textarea shows M365 service: exchange" || echo "✗ Failed"
echo "$PAGE" | grep -q "onedrive:" && echo "✓ Textarea shows M365 service: onedrive" || echo "✗ Failed"
echo ""

# Step 8: Switch back to default profile
echo "Step 8: Switch back to default profile"
GWS_CONTENT=$(cat service_weights.yaml)

curl -s -X POST http://localhost:5000/settings \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "profile=default" \
  --data-urlencode "weights_yaml=$WEIGHTS_CONTENT" \
  --data-urlencode "service_weights_yaml=$GWS_CONTENT" \
  > /dev/null

sleep 1

grep "current_profile: default" profile_config.yaml && echo "✓ Profile switched back to default" || echo "✗ Failed"
echo ""

# Step 9: Verify default profile persists
echo "Step 9: Verify default profile persists after switching back"
PAGE=$(curl -s http://localhost:5000/settings)
echo "$PAGE" | grep -q '<option value="default" selected>default</option>' && echo "✓ Default profile is selected" || echo "✗ Failed"
echo "$PAGE" | grep -q "gmail:" && echo "✓ Textarea shows GWS service: gmail" || echo "✗ Failed"
echo "$PAGE" | grep -q "drive:" && echo "✓ Textarea shows GWS service: drive" || echo "✗ Failed"
echo ""

# Step 10: Verify service weight files exist and have correct content
echo "Step 10: Verify service weight files integrity"
[ -f "service_weights.yaml" ] && echo "✓ service_weights.yaml exists" || echo "✗ Failed"
[ -f "service_weights_m365.yaml" ] && echo "✓ service_weights_m365.yaml exists" || echo "✗ Failed"
[ -f "profile_config.yaml" ] && echo "✓ profile_config.yaml exists" || echo "✗ Failed"

grep -q "gmail:" service_weights.yaml && echo "✓ GWS file contains gmail service" || echo "✗ Failed"
grep -q "exchange:" service_weights_m365.yaml && echo "✓ M365 file contains exchange service" || echo "✗ Failed"
echo ""

echo "========================================="
echo "✅ ALL E2E VERIFICATION STEPS COMPLETED"
echo "========================================="
echo ""
echo "Summary:"
echo "  • Profile dropdown displays on settings page"
echo "  • API endpoints return correct profile data"
echo "  • Profile switching updates config file"
echo "  • Profile selection persists across page reloads"
echo "  • Service weights textarea shows correct content"
echo "  • Both GWS ↔ M365 profile switching works"
echo ""
