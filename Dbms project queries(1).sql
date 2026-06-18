SELECT COUNT(*) INTO v_count
FROM allocation
WHERE student_id = p_student_id
AND exit_time IS NULL;

IF v_count > 0 THEN
   RAISE_APPLICATION_ERROR(-20003, 'Student already inside');
END IF;