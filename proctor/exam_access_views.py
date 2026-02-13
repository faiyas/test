# New API endpoints for exam access control

@api_view(['GET'])
def check_exam_access(request):
    """Check if student can take the exam"""
    candidate_id = request.query_params.get('candidate_id')
    
    if not candidate_id:
        return Response({'error': 'Candidate ID required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if student has completed exam
    completed_session = ExamSession.objects.filter(
        candidate_id=candidate_id,
        completed=True
    ).order_by('-started_at').first()
    
    if completed_session and not completed_session.can_retake:
        return Response({
            'can_take_exam': False,
            'reason': 'already_completed',
            'retake_requested': completed_session.retake_requested,
            'session_id': completed_session.id
        })
    
    return Response({'can_take_exam': True})


@api_view(['POST'])
def request_retake(request):
    """Student requests permission to retake exam"""
    candidate_id = request.data.get('candidate_id')
    reason = request.data.get('reason', '')
    
    if not candidate_id:
        return Response({'error': 'Candidate ID required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Find the most recent completed session
    session = ExamSession.objects.filter(
        candidate_id=candidate_id,
        completed=True
    ).order_by('-started_at').first()
    
    if not session:
        return Response({'error': 'No completed session found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Update retake request
    session.retake_requested = True
    session.retake_reason = reason
    session.save()
    
    print(f"📝 RETAKE REQUEST from {candidate_id}: {reason}")
    
    return Response({
        'message': 'Retake request submitted successfully',
        'session_id': session.id
    })
