from django.contrib.auth.models import Group, User
from rest_framework import permissions, viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets
from .models import Company, Comment
from .serializers import CompanySerializer
from api.serializers import GroupSerializer, UserSerializer, CommentSerializer
from api.tasks import queue_scrape_company
from django.views.generic import TemplateView
from django.shortcuts import get_object_or_404


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all().order_by('name')
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny] 
    serializer_class = UserSerializer


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'

    @action(detail=False, methods=['get'], url_path='get')
    def get_company(self, request):
        try:
            slug = request.query_params.get('slug', '').strip()
            print("Fetching company with slug:", slug)
            company = Company.objects.get(slug=slug)
            if company.is_processed:
                serializer = self.get_serializer(company)
                return Response({
                    'status': 'success',
                    'message': 'Company information retrieved successfully.',
                    'company': serializer.data
                })
            else:
                return Response({
                    'status': 'error',
                    'message': 'Company information is still being processed. Please check back later.',
                    'company': None
                })

        except Company.DoesNotExist:
            return Response({
                    'status': 'error',
                    'message': 'Company not found.',
                    'company': None
                })

    @action(detail=False, methods=['get'], url_path='recent')
    def recent_companies(self, request):
        recent_companies = Company.objects.filter(is_processed=True).order_by('-last_updated')[:3]
        serializer = self.get_serializer(recent_companies, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='search')
    def search_company(self, request):
        url = request.query_params.get('url', '').strip()
        
        if not url:
            return Response(
                {'status': 'error', 'message': 'URL is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Try to find existing company
            company = Company.objects.get(url=url)

            if company.is_processed:
                serializer = self.get_serializer(company)
                return Response({
                    'status': 'success',
                    'company': serializer.data
                })
            else:
                # Company exists but still processing
                return Response({
                    'status': 'processing',
                    'message': 'Company information is being gathered. Please check back later.',
                    'company': {
                        'slug': company.slug,
                        'url': company.url,
                        'name': company.name or 'Processing...'
                    }
                }, status=status.HTTP_202_ACCEPTED)

        except Company.DoesNotExist:
            # Create new company entry with placeholder data
            try:
                company = Company.objects.create(
                    url=url,
                    name=f'Processing {url}...',
                    is_processed=False
                )
                
                # Start scraping task with rate limiting queue
                queue_scrape_company.delay(url)

                return Response({
                    'status': 'processing',
                    'message': 'Company search initiated. Gathering information...',
                    'company': {
                        'slug': company.slug,
                        'url': company.url,
                        'name': company.name
                    }
                }, status=status.HTTP_202_ACCEPTED)

            except Exception as e:
                print(f"Error creating company entry: {e}")
                return Response({
                    'status': 'error',
                    'message': 'Unable to process the URL. Please try again later.'
                }, status=status.HTTP_400_BAD_REQUEST)
        
class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        company = Company.objects.get(slug=self.kwargs['company_slug'])
        # Check if user already has a comment for this company
        existing_comment = Comment.objects.filter(
            user=self.request.user, 
            company=company
        ).first()
        
        if existing_comment:
            # Update existing comment
            serializer.instance = existing_comment
            serializer.save(user=self.request.user, company=company)
        else:
            # Create new comment
            serializer.save(user=self.request.user, company=company)

    def perform_update(self, serializer):
        company = Company.objects.get(slug=self.kwargs['company_slug'])
        # Only allow users to update their own comments
        if serializer.instance.user != self.request.user:
            raise permissions.PermissionDenied("You can only edit your own comments")
        serializer.save(user=self.request.user, company=company)

    def get_queryset(self):
        return self.queryset.filter(company__slug=self.kwargs['company_slug'])

class CompanyBadgeWidgetView(TemplateView):
    template_name = "badge_embed.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company_slug = kwargs.get('company_slug')
        try:
            print("Fetching company with slug:", company_slug)
            company = get_object_or_404(Company, slug=company_slug)
            context['company'] = company
            context['status'] = 'success'
        except:
            context['status'] = 'error'
            context['message'] = 'Company not found'
        return context
