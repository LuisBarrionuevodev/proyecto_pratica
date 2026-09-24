from __future__ import annotations



from typing import Any, Dict, Optional



from app.database import db

from app.domains.actuaciones.attach.oficio import attach_oficio

from app.domains.actuaciones.queries.expediente_vigente import expedientes_vigentes

from app.domains.actuaciones.services.expediente_reactivacion_service import (

    aplicar_reactivacion_respuesta_oficio,

    buscar_expediente_respuesta_oficio_reactivable,

)

from app.domains.actuaciones.presenters.actuacion_presenters import expediente_envio_por_comprobacion

from app.domains.actuaciones.services.oficio_materializacion_service import (

    materializar_iniciador_tras_oficio_documental,

)

from app.domains.rutas_trabajo.services.auth_service import resolve_actor_user_id

from app.models import Actuaciones, Comprobacion, Expediente, JuzgadoCatalogo

from app.utils.actas import acta_6





def _expediente_respuesta_activo_por_oficio(

    comprobacion_id: int,

    oficio_id: int,

) -> Expediente | None:

    """Expediente de respuesta vigente vinculado a un oficio concreto de la comprobación."""

    return (

        Expediente.query.filter(

            Expediente.comprobacion_id == comprobacion_id,

            Expediente.oficio_id == oficio_id,

            Expediente.deleted_at.is_(None),

        )

        .first()

    )





def _validar_prerequisito_expediente_envio(act: Actuaciones, comp: Comprobacion) -> Optional[Expediente]:

    """

    Exige expediente de envío activo o declaración explícita sin expediente.



    Retorno:

        Expediente de envío si existe; None si la comprobación declaró sin expediente.



    Errores:

        LookupError: no hay expediente ni declaración.

    """

    expediente_original = expediente_envio_por_comprobacion(int(comp.id))

    if expediente_original:

        return expediente_original

    if comp.sin_expediente_envio:

        return None

    raise LookupError(

        "No existe expediente de envío para esta comprobación ni declaración de ausencia documental"

    )





def complete_oficio_from_actuacion(

    actuacion_id: int, data: Dict[str, Any], *, actor_user_id: int | None = None

) -> Dict[str, Any]:

    """

    **Esperando oficio:** flujo sobre actuación con comprobación.



    - Valida rama COMPROBACION.

    - Exige **expediente de envío** (`oficio_id` NULL) ya creado **o**

      ``comprobacion.sin_expediente_envio`` declarado explícitamente.

    - Crea o actualiza `Oficio` (misma comprobación) vía `attach_oficio`.

    - Crea **expediente de respuesta de oficio** por ``oficio_id``.

    - Materializa iniciador solo si ``actuacion.domicilio_id`` está presente;

      si no, ``iniciador_materializacion_estado = PENDIENTE_DOMICILIO``.



    Errores:

    - LookupError: 404 (actuación, juzgado o prerequisito expediente)

    - ValueError: 400 (payload inválido)

    - RuntimeError: 409 (conflictos de consistencia/duplicados)

    """

    uid = resolve_actor_user_id(actor_user_id)

    act = db.session.get(Actuaciones, actuacion_id)

    if not act:

        raise LookupError("Actuación no encontrada")



    if act.comprobacion_id is None:

        raise RuntimeError("La actuación no pertenece al flujo COMPROBACION")



    comp = db.session.get(Comprobacion, int(act.comprobacion_id))

    if comp is None or comp.deleted_at is not None:

        raise LookupError("Comprobación no encontrada")



    expediente_original = _validar_prerequisito_expediente_envio(act, comp)



    juzgado = db.session.get(JuzgadoCatalogo, int(data["juzgado_id"]))

    if not juzgado:

        raise LookupError("Juzgado no encontrado")



    numero_exp_oficio = acta_6(data.get("numero_expediente_oficio"))

    fecha_oficio = data["fecha_oficio"]

    fecha_expediente_oficio = data.get("fecha_expediente_oficio") or fecha_oficio

    if fecha_expediente_oficio != fecha_oficio:

        fecha_expediente_oficio = fecha_oficio

    if not numero_exp_oficio or fecha_expediente_oficio is None:

        raise ValueError("numero_expediente_oficio y fecha_expediente_oficio son obligatorios")

    anio_exp_oficio = str(fecha_expediente_oficio.year)



    oficio = attach_oficio(

        {

            "numero": data["numero_oficio"],

            "anio": int(fecha_oficio.year),

            "fecha_oficio": fecha_oficio,

            "juzgado_id": int(data["juzgado_id"]),

            "causa": data.get("causa"),

        },

        comprobacion_id=act.comprobacion_id,

    )

    if not oficio:

        raise ValueError("No se pudo crear/actualizar oficio")



    activo = _expediente_respuesta_activo_por_oficio(

        int(act.comprobacion_id),

        int(oficio.id),

    )

    if activo:

        if activo.fecha_expediente != fecha_expediente_oficio:

            activo.fecha_expediente = fecha_expediente_oficio

            activo.anio = anio_exp_oficio

            db.session.add(activo)

        expediente_respuesta = activo

    elif (

        reactivable := buscar_expediente_respuesta_oficio_reactivable(

            comprobacion_id=int(act.comprobacion_id),

            oficio_id=int(oficio.id),

            numero_expediente=numero_exp_oficio,

            anio=anio_exp_oficio,

        )

    ):

        dup_otro = (

            expedientes_vigentes(

                Expediente.query.filter_by(

                    numero_expediente=numero_exp_oficio,

                    anio=anio_exp_oficio,

                ).filter(Expediente.id != reactivable.id)

            ).first()

        )

        if dup_otro:

            raise RuntimeError("Ese expediente de respuesta de oficio ya existe")

        aplicar_reactivacion_respuesta_oficio(

            reactivable,

            fecha_expediente=fecha_expediente_oficio,

            anio_str=anio_exp_oficio,

        )

        db.session.add(reactivable)

        expediente_respuesta = reactivable

    else:

        dup_expediente = (

            expedientes_vigentes(

                Expediente.query.filter_by(

                    numero_expediente=numero_exp_oficio,

                    anio=anio_exp_oficio,

                )

            ).first()

        )

        if dup_expediente:

            raise RuntimeError("Ese expediente de respuesta de oficio ya existe")



        expediente_respuesta = Expediente(

            numero_expediente=numero_exp_oficio,

            fecha_expediente=fecha_expediente_oficio,

            anio=anio_exp_oficio,

            tipo_expediente="RESPUESTA_OFICIO",

            comprobacion_id=act.comprobacion_id,

            oficio_id=oficio.id,

        )

        db.session.add(expediente_respuesta)



    db.session.flush()



    iniciador_ruta = materializar_iniciador_tras_oficio_documental(

        act,

        oficio,

        expediente_respuesta,

        actor_user_id=uid,

    )



    db.session.commit()



    return {

        "actuacion": act,

        "oficio": oficio,

        "expediente_original": expediente_original,

        "expediente_respuesta_oficio": expediente_respuesta,

        "iniciador_ruta": iniciador_ruta,

        "iniciador_materializacion_estado": oficio.iniciador_materializacion_estado,

    }


