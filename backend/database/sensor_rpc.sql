-- Installed by migration 0002 on PostgreSQL. No anonymous or direct table access.
CREATE OR REPLACE FUNCTION public.sync_spot(p_detected boolean)
RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    v_subject text;
    v_spot public.parking_spot%ROWTYPE;
    v_status text;
BEGIN
    IF p_detected IS NULL THEN
        RAISE EXCEPTION 'Occupancy is required' USING ERRCODE = '22023';
    END IF;
    v_subject := (NULLIF(current_setting('request.jwt.claims', true), '')::jsonb)->>'sub';
    SELECT p.* INTO v_spot FROM public.parking_spot p
        JOIN public.sensor_device d ON d.spot_id = p.id
        WHERE d.subject = v_subject FOR UPDATE OF p;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Device is not provisioned' USING ERRCODE = '42501';
    END IF;
    -- A physical observation must not override an administrator's maintenance flag.
    IF v_spot.status = 'OUT_OF_SERVICE' THEN RETURN v_spot.status; END IF;
    v_status := CASE WHEN p_detected THEN 'OCCUPIED' ELSE 'FREE' END;
    IF v_spot.status IS DISTINCT FROM v_status THEN
        INSERT INTO public.spot_history
            (spot_id, old_status, new_status, changed_at, source, note)
            VALUES (v_spot.id, v_spot.status, v_status, timezone('utc', now()), 'SENSOR', 'Device occupancy update');
        UPDATE public.parking_spot SET status = v_status,
            last_updated = timezone('utc', now()) WHERE id = v_spot.id;
    END IF;
    RETURN v_status;
END;
$$;
REVOKE ALL ON FUNCTION public.sync_spot(boolean) FROM PUBLIC;
ALTER TABLE public.admin_user ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.parking_zone ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.parking_spot ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.spot_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sensor_device ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        REVOKE ALL ON public.admin_user, public.parking_zone, public.parking_spot,
            public.spot_history, public.sensor_device FROM anon;
        REVOKE ALL ON FUNCTION public.sync_spot(boolean) FROM anon;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        REVOKE ALL ON public.admin_user, public.parking_zone, public.parking_spot,
            public.spot_history, public.sensor_device FROM authenticated;
        GRANT EXECUTE ON FUNCTION public.sync_spot(boolean) TO authenticated;
    END IF;
END;
$$;
