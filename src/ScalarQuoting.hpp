#pragma once

#include <ostream>
#include <string>
#include <yaml-cpp/yaml.h>

namespace compose::detail {

// True if writing `value` as a plain (unquoted) scalar would make a YAML 1.1
// or 1.2 core-schema resolver read it back as something other than a string
// (bool, null, int, float, timestamp, merge key), or if the plain form is not
// portable across parsers (e.g. a leading ':' inside a flow sequence).
bool plainScalarChangesType(const std::string& value);

// Writes a string value into `node`. yaml-cpp keeps the node's "!" tag (the
// marker for a scalar that was quoted in the source) across string
// assignment, so a quoted value stays quoted; a new or previously plain value
// is marked for quoting only when its plain form would change type.
void assignString(YAML::Node node, const std::string& value);

// A fresh string scalar, marked for quoting when its plain form would change
// type. Use for sequence entries built through the API.
YAML::Node makeString(const std::string& value);

// Serializes `root` exactly as yaml-cpp's own Node emitter does (same
// anchors/aliases, tags, flow/block styles, key order) except that scalars
// carrying the "!" tag are written double-quoted instead of being left to
// yaml-cpp's plain-scalar heuristic, which only checks for null-like strings.
void emitPreservingQuotes(std::ostream& out, const YAML::Node& root);

} // namespace compose::detail
