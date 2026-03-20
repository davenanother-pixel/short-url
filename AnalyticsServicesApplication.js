// AnalyticsServiceApplication.java
package com.urlshortener.analytics;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class AnalyticsServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(AnalyticsServiceApplication.class, args);
    }
}

// AnalyticsController.java
package com.urlshortener.analytics.controller;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

@RestController
public class AnalyticsController {
    
    @Autowired
    private AnalyticsService analyticsService;
    
    @PostMapping("/log")
    public Map<String, String> logCreation(@RequestBody Map<String, Object> data) {
        String shortCode = (String) data.get("short_code");
        String ip = (String) data.get("ip");
        String userAgent = (String) data.get("user_agent");
        
        analyticsService.logCreation(shortCode, ip, userAgent);
        return Map.of("status", "logged");
    }
    
    @PostMapping("/click")
    public Map<String, String> logClick(@RequestBody Map<String, Object> data) {
        String shortCode = (String) data.get("short_code");
        String ip = (String) data.get("ip");
        String referer = (String) data.get("referer");
        
        analyticsService.logClick(shortCode, ip, referer);
        return Map.of("status", "click logged");
    }
    
    @GetMapping("/stats/{shortCode}")
    public Map<String, Object> getStats(@PathVariable String shortCode) {
        return analyticsService.getStats(shortCode);
    }
}

// AnalyticsService.java
package com.urlshortener.analytics.service;

import org.springframework.stereotype.Service;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

@Service
public class AnalyticsService {
    
    private final Map<String, URLAnalytics> analytics = new ConcurrentHashMap<>();
    
    public void logCreation(String shortCode, String ip, String userAgent) {
        URLAnalytics urlStats = analytics.computeIfAbsent(shortCode, 
            k -> new URLAnalytics());
        urlStats.incrementCreations();
        urlStats.addCreationIp(ip);
    }
    
    public void logClick(String shortCode, String ip, String referer) {
        URLAnalytics urlStats = analytics.computeIfAbsent(shortCode,
            k -> new URLAnalytics());
        urlStats.incrementClicks();
        urlStats.addClick(ip, referer);
    }
    
    public Map<String, Object> getStats(String shortCode) {
        URLAnalytics urlStats = analytics.get(shortCode);
        if (urlStats == null) {
            return Collections.emptyMap();
        }
        
        Map<String, Object> result = new HashMap<>();
        result.put("short_code", shortCode);
        result.put("total_clicks", urlStats.getTotalClicks());
        result.put("total_creations", urlStats.getTotalCreations());
        result.put("unique_ips", urlStats.getUniqueIps().size());
        result.put("top_referers", urlStats.getTopReferers(5));
        
        return result;
    }
    
    // Inner class for analytics tracking
    private static class URLAnalytics {
        private final AtomicLong totalClicks = new AtomicLong(0);
        private final AtomicLong totalCreations = new AtomicLong(0);
        private final Set<String> uniqueIps = ConcurrentHashMap.newKeySet();
        private final Map<String, AtomicLong> refererCounts = new ConcurrentHashMap<>();
        private final Set<String> creationIps = ConcurrentHashMap.newKeySet();
        
        public void incrementClicks() { totalClicks.incrementAndGet(); }
        public void incrementCreations() { totalCreations.incrementAndGet(); }
        
        public void addClick(String ip, String referer) {
            uniqueIps.add(ip);
            if (referer != null && !referer.isEmpty()) {
                refererCounts.computeIfAbsent(referer, k -> new AtomicLong())
                             .incrementAndGet();
            }
        }
        
        public void addCreationIp(String ip) {
            creationIps.add(ip);
        }
        
        public long getTotalClicks() { return totalClicks.get(); }
        public long getTotalCreations() { return totalCreations.get(); }
        public Set<String> getUniqueIps() { return uniqueIps; }
        
        public List<Map.Entry<String, Long>> getTopReferers(int limit) {
            return refererCounts.entrySet().stream()
                .sorted(Map.Entry.<String, AtomicLong>comparingByValue()
                    .reversed())
                .limit(limit)
                .map(e -> Map.entry(e.getKey(), e.getValue().get()))
                .toList();
        }
    }
}
