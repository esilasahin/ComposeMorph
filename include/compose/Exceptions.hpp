#pragma once
#include <stdexcept>
#include <string>

namespace compose {

class ComposeException : public std::runtime_error {
public:
    explicit ComposeException(const std::string& message) : std::runtime_error(message) {}
};

class ParseException : public ComposeException {
public:
    explicit ParseException(const std::string& message) : ComposeException("Parse Error: " + message) {}
};

class ValidationException : public ComposeException {
public:
    explicit ValidationException(const std::string& message) : ComposeException("Validation Error: " + message) {}
};

class ServiceNotFoundException : public ComposeException {
public:
    explicit ServiceNotFoundException(const std::string& serviceName)
        : ComposeException("Service not found: " + serviceName) {}
};

class InvalidPropertyException : public ComposeException {
public:
    explicit InvalidPropertyException(const std::string& message)
        : ComposeException("Invalid Property: " + message) {}
};

} // namespace compose