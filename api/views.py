from django.contrib.auth.models import Group, User
from rest_framework import permissions, viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets
from scraper.builtwith_scraper import run_search_scraper_light
from .models import Company, Comment
from .serializers import CompanySerializer
from api.serializers import GroupSerializer, UserSerializer, CommentSerializer
from scraper.tasks import scrape_company_task
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
            # Do a quick check if the URL is valid and contains company info
            try:
                quick_check = run_search_scraper_light(url)
                if not quick_check.get('name'):
                    return Response({
                        'status': 'error',
                        'message': 'No company information found at this URL.'
                    }, status=status.HTTP_404_NOT_FOUND)
                
                # Create new company entry
                company = Company.objects.create(
                    url=url,
                    name=quick_check.get('name', 'Processing...'),
                    is_processed=False
                )

                # Start scraping task
                scrape_company_task.delay(url)

                return Response({
                    'status': 'processing',
                    'message': 'Company found! Gathering detailed information...',
                    'company': {
                        'slug': company.slug,
                        'url': company.url,
                        'name': company.name
                    }
                }, status=status.HTTP_202_ACCEPTED)

            except Exception as e:
                return Response({
                    'status': 'error',
                    'message': 'Unable to access or validate the URL. Please check the URL and try again.'
                }, status=status.HTTP_400_BAD_REQUEST)
        
class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        company = Company.objects.get(slug=self.kwargs['company_slug'])
        serializer.save(user=self.request.user, company=company)

    def get_queryset(self):
        return self.queryset.filter(company__slug=self.kwargs['company_slug'])

class CompanyBadgeWidgetView(TemplateView):
    template_name = "badge_embed.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = get_object_or_404(Company, id=kwargs['company_id'])
        context['company'] = company
        return context