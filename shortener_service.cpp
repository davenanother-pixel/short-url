// shortener_service.cpp
#include <iostream>
#include <string>
#include <unordered_set>
#include <mutex>
#include <chrono>
#include <random>
#include <httplib.h>  // Using cpp-httplib library

class ShortenerService {
private:
    std::unordered_set<std::string> existing_codes;
    std::mutex mtx;
    const std::string BASE62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";
    
    // High-performance hash function
    uint64_t fast_hash(const std::string& str) {
        uint64_t hash = 0xcbf29ce484222325;
        for (char c : str) {
            hash ^= c;
            hash *= 0x100000001b3;
        }
        return hash;
    }
    
    std::string to_base62(uint64_t num, int length = 6) {
        std::string result;
        while (num > 0 && result.length() < length) {
            result = BASE62[num % 62] + result;
            num /= 62;
        }
        return result;
    }
    
public:
    std::string generate_code(const std::string& url, const std::string& custom_code = "") {
        std::lock_guard<std::mutex> lock(mtx);
        
        // Handle custom code
        if (!custom_code.empty()) {
            if (existing_codes.find(custom_code) != existing_codes.end()) {
                throw std::runtime_error("Custom code already exists");
            }
            existing_codes.insert(custom_code);
            return custom_code;
        }
        
        // Generate unique code using hash + timestamp
        uint64_t timestamp = std::chrono::duration_cast<std::chrono::nanoseconds>(
            std::chrono::system_clock::now().time_since_epoch()
        ).count();
        
        uint64_t hash = fast_hash(url + std::to_string(timestamp));
        std::string code = to_base62(hash);
        
        // Ensure uniqueness
        while (existing_codes.find(code) != existing_codes.end()) {
            hash = fast_hash(code + std::to_string(timestamp++));
            code = to_base62(hash);
        }
        
        existing_codes.insert(code);
        return code;
    }
    
    bool validate_url(const std::string& url) {
        // Quick validation
        return url.find("http://") == 0 || url.find("https://") == 0;
    }
};

int main() {
    ShortenerService service;
    httplib::Server svr;
    
    // CORS headers
    svr.set_pre_routing_handler([](const httplib::Request& req, httplib::Response& res) {
        res.set_header("Access-Control-Allow-Origin", "*");
        res.set_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS");
        return httplib::Server::HandlerResponse::Unhandled;
    });
    
    // Generate short code endpoint
    svr.Post("/generate", [&](const httplib::Request& req, httplib::Response& res) {
        auto json = nlohmann::json::parse(req.body);
        
        std::string url = json["url"];
        std::string custom = json.value("custom_code", "");
        
        if (!service.validate_url(url)) {
            res.status = 400;
            res.set_content("{\"error\": \"Invalid URL format\"}", "application/json");
            return;
        }
        
        try {
            std::string code = service.generate_code(url, custom);
            nlohmann::json response = {
                {"short_code", code},
                {"status", "success"}
            };
            res.set_content(response.dump(), "application/json");
        } catch (const std::exception& e) {
            res.status = 400;
            nlohmann::json error = {{"error", e.what()}};
            res.set_content(error.dump(), "application/json");
        }
    });
    
    std::cout << "Shortener Service running on port 8081" << std::endl;
    svr.listen("0.0.0.0", 8081);
    
    return 0;
}
