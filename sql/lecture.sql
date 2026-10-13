-- Compte en lecture seule pour le tableau de bord (SELECT uniquement).
-- Usage : psql "$DATABASE_URL" -v mdp="'...'" -f sql/lecture.sql
-- Le mot de passe n'est jamais écrit dans le dépôt.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'bvc_lecture') THEN
        CREATE ROLE bvc_lecture LOGIN;
    END IF;
END
$$;
ALTER ROLE bvc_lecture WITH LOGIN PASSWORD :mdp;
GRANT CONNECT ON DATABASE :"DBNAME" TO bvc_lecture;
GRANT USAGE ON SCHEMA public TO bvc_lecture;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO bvc_lecture;
-- Tables créées plus tard par le propriétaire (par exemple alerts) : lecture aussi.
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO bvc_lecture;
