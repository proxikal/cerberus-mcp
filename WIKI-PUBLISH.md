# Publishing the Wiki

The comprehensive wiki documentation has been created in `wiki-content/` directory. Here's how to publish it to GitHub.

## What's Been Created

**7 comprehensive wiki pages (2,949 lines total):**

1. **Home.md** - Welcome page with navigation
2. **Installation.md** - Detailed setup guide for all components
3. **Quick-Start.md** - Get productive in 5 minutes
4. **MCP-Tools-Reference.md** - All 51 tools documented with examples
5. **Token-Efficiency.md** - Deep dive on 70-95% token savings
6. **Context-Aware-Operation.md** - Project vs general mode explained
7. **FAQ.md** - Frequently asked questions

## Publishing Steps

### Option 1: Automatic (Using Script)

```bash
# Initialize the wiki repo first (one-time)
# Go to GitHub: https://github.com/proxikal/cerberus-mcp/wiki
# Click "Create the first page"
# Title: "Home"
# Content: "Initializing wiki..."
# Click "Save Page"

# Now run the publish script
./publish-wiki.sh
```

The script will:
1. Clone the wiki repo
2. Copy all wiki pages
3. Commit and push

### Option 2: Manual

```bash
# 1. Initialize wiki (if not done)
# Go to: https://github.com/proxikal/cerberus-mcp/wiki
# Click "Create the first page" → Save any content

# 2. Clone wiki repo
git clone https://github.com/proxikal/cerberus-mcp.wiki.git
cd cerberus-mcp.wiki

# 3. Copy wiki pages
cp ../wiki-content/*.md .

# 4. Commit and push
git add *.md
git commit -m "Add comprehensive Cerberus documentation"
git push

# 5. View published wiki
# https://github.com/proxikal/cerberus-mcp/wiki
```

## Verification

After publishing, check:

- **Home page**: https://github.com/proxikal/cerberus-mcp/wiki
- **All pages appear** in the sidebar
- **Links work** between pages
- **Formatting looks correct**

## Updating Wiki

When you update wiki content:

```bash
# 1. Edit files in wiki-content/
# 2. Run publish script again
./publish-wiki.sh
```

## README Updated

The main README has been slimmed down from **824 lines to 175 lines** (79% reduction).

**Old README:** Tried to explain everything inline
**New README:** Focuses on quick start, links to wiki for details

All detailed documentation is now in the wiki where it belongs.

## What This Achieves

✅ **README is concise** - Quick overview and setup
✅ **Wiki is comprehensive** - Detailed guides for everything
✅ **Better discoverability** - Users can find specific topics
✅ **Easier maintenance** - Update wiki without cluttering README
✅ **Better for developers** - Deep dives available without overwhelming newcomers

---

**Next step:** Initialize the wiki and run `./publish-wiki.sh`
