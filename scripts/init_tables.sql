-- Content Supply Platform — MySQL DDL
-- Target database: rec_platform

CREATE TABLE IF NOT EXISTS `cs_feeds` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(255) NOT NULL,
    `url` VARCHAR(1024) NOT NULL UNIQUE,
    `source_type` ENUM('rss','atom','web','hot_search') DEFAULT 'rss',
    `category` VARCHAR(100) DEFAULT '',
    `poll_interval` INT DEFAULT 1800,
    `last_fetched_at` DATETIME NULL,
    `last_error` TEXT NULL,
    `error_count` INT DEFAULT 0,
    `status` ENUM('active','paused','error') DEFAULT 'active',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `cs_items` (
    `id` VARCHAR(64) PRIMARY KEY,
    `title` VARCHAR(500) NOT NULL,
    `summary` TEXT NULL,
    `content` MEDIUMTEXT NULL,
    `original_content` MEDIUMTEXT NULL,
    `url` VARCHAR(1024) NOT NULL UNIQUE,
    `image_url` VARCHAR(1024) NULL,
    `author` VARCHAR(255) NULL,
    `source_name` VARCHAR(255) NULL,
    `source_type` ENUM('rss','web','hot_keyword','manual') DEFAULT 'rss',
    `feed_id` INT NULL,
    `hot_keyword_id` INT NULL,
    `content_type` ENUM('article','video','post') DEFAULT 'article',
    `tags` JSON NULL,
    `category` VARCHAR(100) NULL,
    `quality_score` FLOAT DEFAULT 0.0,
    `content_hash` VARCHAR(64) NOT NULL UNIQUE,
    `is_rewritten` BOOLEAN DEFAULT FALSE,
    `rewrite_task_id` INT NULL,
    `exposure_count` INT DEFAULT 0,
    `click_count` INT DEFAULT 0,
    `status` ENUM('draft','published','archived') DEFAULT 'published',
    `published_at` DATETIME NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_source_type` (`source_type`),
    INDEX `idx_category` (`category`),
    INDEX `idx_status` (`status`),
    INDEX `idx_quality` (`quality_score`),
    INDEX `idx_created_at` (`created_at`),
    INDEX `idx_feed_id` (`feed_id`),
    FOREIGN KEY (`feed_id`) REFERENCES `cs_feeds`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `cs_crawl_tasks` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `feed_id` INT NULL,
    `hot_keyword_id` INT NULL,
    `url` VARCHAR(1024) NOT NULL,
    `task_type` ENUM('rss','web','manual','hot_keyword') NOT NULL,
    `status` ENUM('pending','running','done','failed') DEFAULT 'pending',
    `items_found` INT DEFAULT 0,
    `items_new` INT DEFAULT 0,
    `error_message` TEXT NULL,
    `started_at` DATETIME NULL,
    `finished_at` DATETIME NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_status` (`status`),
    INDEX `idx_task_type` (`task_type`),
    FOREIGN KEY (`feed_id`) REFERENCES `cs_feeds`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `cs_hot_keywords` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `keyword` VARCHAR(255) NOT NULL,
    `platform` VARCHAR(50) NOT NULL,
    `rank` INT DEFAULT 0,
    `hot_score` FLOAT DEFAULT 0.0,
    `category` VARCHAR(100) NULL,
    `fetched_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `status` ENUM('pending','fetched','processing','done') DEFAULT 'fetched',
    `content_fetched` BOOLEAN DEFAULT FALSE,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_platform` (`platform`),
    INDEX `idx_keyword_platform` (`keyword`, `platform`),
    INDEX `idx_fetched_at` (`fetched_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `cs_rewrite_tasks` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `item_id` VARCHAR(64) NOT NULL,
    `rewrite_type` ENUM('paraphrase','summarize','expand') NOT NULL,
    `status` ENUM('pending','running','done','failed') DEFAULT 'pending',
    `original_hash` VARCHAR(64) NULL,
    `llm_model` VARCHAR(100) NULL,
    `prompt_used` TEXT NULL,
    `error_message` TEXT NULL,
    `started_at` DATETIME NULL,
    `finished_at` DATETIME NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_item_id` (`item_id`),
    INDEX `idx_status` (`status`),
    FOREIGN KEY (`item_id`) REFERENCES `cs_items`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `cs_cleanup_logs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `policy` VARCHAR(50) NOT NULL,
    `source_type` VARCHAR(50) NOT NULL,
    `status` ENUM('pending_review','approved','rejected','executing','done','expired') DEFAULT 'pending_review',
    `items_scanned` INT DEFAULT 0,
    `items_to_delete` INT DEFAULT 0,
    `items_deleted` INT DEFAULT 0,
    `space_freed_mb` FLOAT DEFAULT 0.0,
    `pending_item_ids` JSON NULL,
    `notification_sent` BOOLEAN DEFAULT FALSE,
    `notification_channel` VARCHAR(50) NULL,
    `reviewed_by` VARCHAR(100) NULL,
    `reviewed_at` DATETIME NULL,
    `auto_confirm_at` DATETIME NULL,
    `details` JSON NULL,
    `started_at` DATETIME NULL,
    `finished_at` DATETIME NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_status` (`status`),
    INDEX `idx_policy` (`policy`),
    INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
