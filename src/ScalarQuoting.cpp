#include "ScalarQuoting.hpp"

#include <yaml-cpp/anchor.h>

#include <regex>
#include <unordered_map>
#include <vector>

#include "compose/Exceptions.hpp"

namespace compose::detail {

namespace {

// Union of the YAML 1.1 implicit types (as resolved by PyYAML/libyaml-based
// tools) and the YAML 1.2 core schema. Over-quoting a string is harmless;
// under-quoting silently retypes it, so the net is cast wide on purpose.
const std::regex& nonStringPlainScalar() {
    static const std::regex re(
        // null
        "~|null|Null|NULL"
        // bool (YAML 1.1 includes y/n/yes/no/on/off)
        "|y|Y|yes|Yes|YES|n|N|no|No|NO|true|True|TRUE|false|False|FALSE|on|On|ON|off|Off|OFF"
        // int: binary, octal (0o and leading-zero), hex, decimal, sexagesimal
        "|[-+]?0b[0-1_]+|[-+]?0o[0-7]+|[-+]?0x[0-9a-fA-F_]+|[-+]?[0-9][0-9_]*"
        "|[-+]?[1-9][0-9_]*(:[0-5]?[0-9])+"
        // float: decimal, exponent-only, sexagesimal, inf, nan
        "|[-+]?([0-9][0-9_]*)?\\.[0-9_]*([eE][-+]?[0-9]+)?"
        "|[-+]?[0-9][0-9_]*[eE][-+]?[0-9]+"
        "|[-+]?[0-9][0-9_]*(:[0-5]?[0-9])+\\.[0-9_]*"
        "|[-+]?\\.(inf|Inf|INF)|\\.(nan|NaN|NAN)"
        // timestamp (YAML 1.1)
        "|[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}"
        "(([Tt]|[ \\t]+)[0-9]{1,2}:[0-9]{2}:[0-9]{2}(\\.[0-9]*)?"
        "([ \\t]*(Z|[-+][0-9]{1,2}(:[0-9]{2})?))?)?"
        // merge key and value indicator (YAML 1.1)
        "|<<|=");
    return re;
}

// Node identity for alias detection, mirroring yaml-cpp's NodeEvents. The
// source position narrows the Node::is() search to a bucket; nodes created
// through the API have no position and share one bucket.
class RefTracker {
public:
    int& count(const YAML::Node& node) { return entry(node).count; }
    YAML::anchor_t& anchor(const YAML::Node& node) { return entry(node).anchor; }

private:
    struct Entry {
        YAML::Node node;
        int count = 0;
        YAML::anchor_t anchor = 0;
    };

    Entry& entry(const YAML::Node& node) {
        auto& bucket = buckets_[node.Mark().pos];
        for (auto& e : bucket) {
            if (e.node.is(node)) return e;
        }
        bucket.push_back(Entry{node});
        return bucket.back();
    }

    std::unordered_map<int, std::vector<Entry>> buckets_;
};

void countRefs(const YAML::Node& node, RefTracker& refs) {
    if (!node.IsDefined() || ++refs.count(node) > 1) return;
    if (node.IsSequence()) {
        for (const auto& child : node) countRefs(child, refs);
    } else if (node.IsMap()) {
        for (const auto& kv : node) {
            countRefs(kv.first, refs);
            countRefs(kv.second, refs);
        }
    }
}

void emitProps(YAML::Emitter& out, const std::string& tag, YAML::anchor_t anchor) {
    if (!tag.empty() && tag != "?" && tag != "!") out << YAML::VerbatimTag(tag);
    if (anchor) out << YAML::Anchor(std::to_string(anchor));
}

void emitCollectionStyle(YAML::Emitter& out, YAML::EmitterStyle::value style) {
    if (style == YAML::EmitterStyle::Block) {
        out << YAML::Block;
    } else if (style == YAML::EmitterStyle::Flow) {
        out << YAML::Flow;
    }
    out.RestoreGlobalModifiedSettings();
}

void emitNode(YAML::Emitter& out, const YAML::Node& node, RefTracker& refs,
              YAML::anchor_t& lastAnchor) {
    if (!node.IsDefined()) return;

    YAML::anchor_t anchor = 0;
    if (refs.count(node) > 1) {
        YAML::anchor_t& assigned = refs.anchor(node);
        if (assigned) {
            out << YAML::Alias(std::to_string(assigned));
            return;
        }
        assigned = anchor = ++lastAnchor;
    }

    switch (node.Type()) {
        case YAML::NodeType::Null:
            emitProps(out, "", anchor);
            out << YAML::Null;
            break;
        case YAML::NodeType::Scalar:
            emitProps(out, node.Tag(), anchor);
            if (node.Tag() == "!") out << YAML::DoubleQuoted;
            out << node.Scalar();
            break;
        case YAML::NodeType::Sequence:
            emitProps(out, node.Tag(), anchor);
            emitCollectionStyle(out, node.Style());
            out << YAML::BeginSeq;
            for (const auto& child : node) emitNode(out, child, refs, lastAnchor);
            out << YAML::EndSeq;
            break;
        case YAML::NodeType::Map:
            emitProps(out, node.Tag(), anchor);
            emitCollectionStyle(out, node.Style());
            out << YAML::BeginMap;
            for (const auto& kv : node) {
                out << YAML::Key;
                emitNode(out, kv.first, refs, lastAnchor);
                out << YAML::Value;
                emitNode(out, kv.second, refs, lastAnchor);
            }
            out << YAML::EndMap;
            break;
        case YAML::NodeType::Undefined:
            break;
    }
}

} // namespace

bool plainScalarChangesType(const std::string& value) {
    if (value.empty() || value.front() == ':') return true;
    return std::regex_match(value, nonStringPlainScalar());
}

void assignString(YAML::Node node, const std::string& value) {
    node = value;
    const std::string& tag = node.Tag();
    if ((tag.empty() || tag == "?") && plainScalarChangesType(value)) {
        node.SetTag("!");
    }
}

YAML::Node makeString(const std::string& value) {
    YAML::Node node(value);
    if (plainScalarChangesType(value)) node.SetTag("!");
    return node;
}

void emitPreservingQuotes(std::ostream& out, const YAML::Node& root) {
    RefTracker refs;
    countRefs(root, refs);

    YAML::Emitter emitter(out);
    YAML::anchor_t lastAnchor = 0;
    emitNode(emitter, root, refs, lastAnchor);
    if (!emitter.good()) {
        throw ComposeException("YAML emission failed: " + emitter.GetLastError());
    }
}

} // namespace compose::detail
