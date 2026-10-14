ALTER TABLE domain_crawl_policy
ADD COLUMN obey_robots INTEGER NOT NULL DEFAULT 1 CHECK(obey_robots IN (0,1));
