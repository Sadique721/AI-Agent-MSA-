-- Master relational schema for MSA AI AGENT V4.0 Enterprise AI Operating System

-- Enable UUID extension if available
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Core Organizations & Tenants (Module 42)
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Workspaces within Organizations
CREATE TABLE IF NOT EXISTS workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Users Management (Module 41)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'developer',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Agent Instance Registry (Module 39)
CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL, -- planner, coder, memory, research
    status VARCHAR(50) DEFAULT 'offline', -- active, idle, offline
    capabilities JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Workflow DAG instances (Module 34)
CREATE TABLE IF NOT EXISTS workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    definition JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Knowledge Graph Nodes (Module 25)
CREATE TABLE IF NOT EXISTS graph_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    label VARCHAR(100) NOT NULL,
    properties JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Knowledge Graph Edges (Module 25)
CREATE TABLE IF NOT EXISTS graph_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES graph_nodes(id) ON DELETE CASCADE,
    target_id UUID REFERENCES graph_nodes(id) ON DELETE CASCADE,
    relationship_type VARCHAR(100) NOT NULL,
    properties JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Immutable Audit Trails (Module 48)
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(255) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id VARCHAR(255),
    client_ip VARCHAR(45),
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ════════════════════════════════════════════════════════════════════════════
-- V7-V9 Career Intelligence Platform Tables
-- ════════════════════════════════════════════════════════════════════════════

-- Jobs discovered from Adzuna/Jooble/JSearch APIs
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(255) UNIQUE,
    source VARCHAR(100) NOT NULL,              -- adzuna, jooble, jsearch, linkedin
    title VARCHAR(500) NOT NULL,
    company VARCHAR(255),
    location VARCHAR(255),
    description TEXT,
    url TEXT,
    salary_min NUMERIC,
    salary_max NUMERIC,
    currency VARCHAR(10),
    employment_type VARCHAR(100),
    skills_required JSONB,
    ats_score NUMERIC(4,3),                    -- ATS compatibility score (0.0-1.0)
    match_score NUMERIC(4,3),                  -- Semantic match score (0.0-1.0)
    status VARCHAR(50) DEFAULT 'discovered',   -- discovered, queued, applied, rejected
    discovered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Resumes generated per job
CREATE TABLE IF NOT EXISTS resumes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES jobs(id) ON DELETE SET NULL,
    version INTEGER DEFAULT 1,
    content TEXT NOT NULL,
    format VARCHAR(50) DEFAULT 'markdown',     -- markdown, html, pdf
    ats_score NUMERIC(4,3),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Job applications submitted
CREATE TABLE IF NOT EXISTS applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES jobs(id) ON DELETE CASCADE,
    resume_id UUID REFERENCES resumes(id) ON DELETE SET NULL,
    status VARCHAR(100) DEFAULT 'submitted',   -- submitted, viewed, interview, offer, rejected
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    cover_letter TEXT,
    platform VARCHAR(100),
    form_data JSONB,
    error_log TEXT,
    retry_count INTEGER DEFAULT 0
);

-- Interview tracking
CREATE TABLE IF NOT EXISTS interviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID REFERENCES applications(id) ON DELETE CASCADE,
    scheduled_at TIMESTAMP WITH TIME ZONE,
    interview_type VARCHAR(100),               -- phone, video, onsite, technical
    interviewer VARCHAR(255),
    notes TEXT,
    outcome VARCHAR(100),                      -- passed, failed, pending
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Recruiter CRM
CREATE TABLE IF NOT EXISTS recruiters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255),
    email VARCHAR(255),
    company VARCHAR(255),
    linkedin_url TEXT,
    last_contact_at TIMESTAMP WITH TIME ZONE,
    notes TEXT,
    status VARCHAR(100) DEFAULT 'cold',        -- cold, warm, active, responded
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Analytics snapshots
CREATE TABLE IF NOT EXISTS analytics_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    snapshot_type VARCHAR(100),                -- daily, weekly, monthly
    metrics JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ════════════════════════════════════════════════════════════════════════════
-- Performance Indexes
-- ════════════════════════════════════════════════════════════════════════════

-- Core table indexes
CREATE INDEX IF NOT EXISTS idx_workspaces_org_id      ON workspaces (org_id);
CREATE INDEX IF NOT EXISTS idx_users_org_id            ON users (org_id);
CREATE INDEX IF NOT EXISTS idx_users_email             ON users (email);
CREATE INDEX IF NOT EXISTS idx_agents_workspace_id     ON agents (workspace_id);
CREATE INDEX IF NOT EXISTS idx_workflows_workspace_id  ON workflows (workspace_id);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_workspace   ON graph_nodes (workspace_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_source      ON graph_edges (source_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_target      ON graph_edges (target_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id      ON audit_logs (user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at   ON audit_logs (created_at DESC);

-- Career table indexes
CREATE INDEX IF NOT EXISTS idx_jobs_status             ON jobs (status);
CREATE INDEX IF NOT EXISTS idx_jobs_source             ON jobs (source);
CREATE INDEX IF NOT EXISTS idx_jobs_discovered_at      ON jobs (discovered_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_match_score        ON jobs (match_score DESC);
CREATE INDEX IF NOT EXISTS idx_applications_job_id     ON applications (job_id);
CREATE INDEX IF NOT EXISTS idx_applications_status     ON applications (status);
CREATE INDEX IF NOT EXISTS idx_interviews_app_id       ON interviews (application_id);
CREATE INDEX IF NOT EXISTS idx_recruiters_email        ON recruiters (email);

-- ════════════════════════════════════════════════════════════════════════════
-- Create N8N database (run as superuser)
-- ════════════════════════════════════════════════════════════════════════════
SELECT 'CREATE DATABASE msa_n8n'
    WHERE NOT EXISTS (
        SELECT FROM pg_database WHERE datname = 'msa_n8n'
    )\gexec
