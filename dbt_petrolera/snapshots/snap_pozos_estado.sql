-- ===============================================================================
-- snap_pozos_estado: SCD Type 2 sobre el estado del pozo.
-- El estado cambia en el OLTP (seed_oltp.py --refresh). El snapshot mantiene
-- el historial de cambios: cuando `estado` cambia, se cierra la fila anterior
-- (dbt_valid_to) y se abre una nueva. La fuente es stg_pozos (snapshot diario
-- del estado actual cargado desde MinIO por el loader).
-- ===============================================================================
{% snapshot snap_pozos_estado %}
    {{ config(
        target_schema='snapshots',
        unique_key='pozo_id',
        strategy='check',
        check_cols=['estado'],
        invalidate_hard_deletes=True,
    ) }}
    select
        pozo_id,
        oltp_id,
        cuenca,
        fecha_perforacion,
        estado
    from {{ ref('stg_pozos') }}
{% endsnapshot %}